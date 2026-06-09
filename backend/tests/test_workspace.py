"""V3.2 Agent Workspace 集成测试。"""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select, text

from app.database import async_session
from app.main import app
from app.models.user import User
from app.models.path import LearningTask, LearningPathTopic, LearningPathModule, LearningPath
from app.models.agent import AgentRun

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _require_database() -> None:
    try:
        async with async_session() as session:
            await session.execute(text("select 1"))
    except Exception as exc:
        pytest.skip(f"database is not available for V3.2 workspace test: {exc}")


async def _cleanup_users(usernames: list[str]) -> None:
    async with async_session() as session:
        result = await session.execute(select(User.id).where(User.username.in_(usernames)))
        user_ids = result.scalars().all()
        if user_ids:
            # 按依赖顺序删除
            await session.execute(delete(LearningTask).where(LearningTask.user_id.in_(user_ids)))
            for uid in user_ids:
                paths = (await session.execute(select(LearningPath.id).where(LearningPath.user_id == uid))).scalars().all()
                if paths:
                    modules = (await session.execute(select(LearningPathModule.id).where(LearningPathModule.path_id.in_(paths)))).scalars().all()
                    if modules:
                        await session.execute(delete(LearningPathTopic).where(LearningPathTopic.module_id.in_(modules)))
                    await session.execute(delete(LearningPathModule).where(LearningPathModule.path_id.in_(paths)))
                    await session.execute(delete(LearningPath).where(LearningPath.id.in_(paths)))
            await session.execute(delete(AgentRun).where(AgentRun.user_id.in_(user_ids)))
            await session.execute(delete(User).where(User.id.in_(user_ids)))
            await session.commit()


async def _register(client: AsyncClient, username: str, password: str = "secret123") -> str:
    response = await client.post("/api/v1/auth/register", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["data"]["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def test_workspace_diagnose_and_plan_creates_tasks():
    """验证 diagnose-and-plan 端点能创建结构化路径和任务。"""
    await _require_database()
    suffix = uuid.uuid4().hex[:10]
    username = f"v32_ws_{suffix}"

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            token = await _register(client, username)
            headers = _auth(token)

            # 运行诊断 + 规划
            res = await client.post(
                "/api/v1/workspace/diagnose-and-plan",
                headers=headers,
                params={"goal": "学习 AI Agent 应用开发"},
            )
            assert res.status_code == 200, res.text
            data = res.json()["data"]

            # 验证诊断结果
            assert "diagnosis" in data
            assert "summary" in data["diagnosis"]

            # 验证规划结果
            assert "plan" in data
            plan = data["plan"]
            assert plan["path_id"]
            assert plan["modules_count"] > 0
            assert plan["tasks_count"] > 0

            # 验证今日任务
            tasks_res = await client.get("/api/v1/workspace/tasks/today", headers=headers)
            assert tasks_res.status_code == 200
            tasks_data = tasks_res.json()["data"]
            # 任务可能 due_at 在未来，所以不一定在今日任务中
            assert "tasks" in tasks_data

            # 验证 AgentRun 被记录
            runs_res = await client.get("/api/v1/traces/runs", headers=headers)
            assert runs_res.status_code == 200
            assert runs_res.json()["data"]["total"] >= 1

            # 验证学习路径可通过 paths API 查询
            paths_res = await client.get("/api/v1/paths", headers=headers)
            assert paths_res.status_code == 200
            paths = paths_res.json()["data"]
            assert len(paths) >= 1

    finally:
        await _cleanup_users([username])


async def test_task_completion():
    """验证任务完成接口。"""
    await _require_database()
    suffix = uuid.uuid4().hex[:10]
    username = f"v32_task_{suffix}"

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            token = await _register(client, username)
            headers = _auth(token)

            # 先创建一个路径和任务
            await client.post(
                "/api/v1/workspace/diagnose-and-plan",
                headers=headers,
                params={"goal": "学习 Python"},
            )

            # 查询所有任务
            all_tasks = await client.get(
                "/api/v1/workspace/tasks",
                headers=headers,
                params={"page_size": 50},
            )
            assert all_tasks.status_code == 200
            items = all_tasks.json()["data"]["items"]
            assert len(items) > 0

            # 完成第一个任务
            task_id = items[0]["id"]
            complete_res = await client.put(
                f"/api/v1/workspace/tasks/{task_id}/complete",
                headers=headers,
            )
            assert complete_res.status_code == 200
            assert complete_res.json()["data"]["status"] == "completed"

    finally:
        await _cleanup_users([username])
