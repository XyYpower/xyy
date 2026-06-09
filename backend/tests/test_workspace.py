"""V4.1 Agent Workspace 集成测试（preview/approve/reject 流程）。"""

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
        pytest.skip(f"database is not available for V4.1 workspace test: {exc}")


async def _cleanup_users(usernames: list[str]) -> None:
    async with async_session() as session:
        result = await session.execute(select(User.id).where(User.username.in_(usernames)))
        user_ids = result.scalars().all()
        if user_ids:
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


async def test_diagnose_and_plan_preview_then_approve():
    """验证 V4.1 流程：诊断+规划预览 → 审批通过 → 任务创建。"""
    await _require_database()
    suffix = uuid.uuid4().hex[:10]
    username = f"v41_ws_{suffix}"

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            token = await _register(client, username)
            headers = _auth(token)

            # Step 1: 诊断 + 规划预览
            res = await client.post(
                "/api/v1/workspace/diagnose-and-plan",
                headers=headers,
                params={"goal": "学习 AI Agent 应用开发"},
            )
            assert res.status_code == 200, res.text
            data = res.json()["data"]

            # 验证返回 waiting_approval 状态
            assert data["status"] == "waiting_approval"
            run_id = data["run_id"]

            # 验证诊断结果
            assert "diagnosis" in data
            assert "summary" in data["diagnosis"]

            # 验证计划预览（不落库）
            assert "plan_preview" in data
            preview = data["plan_preview"]
            assert preview["modules_count"] > 0
            assert preview["tasks_count"] > 0

            # 验证此时没有任务被创建
            tasks_res = await client.get("/api/v1/workspace/tasks", headers=headers)
            assert tasks_res.status_code == 200
            assert tasks_res.json()["data"]["total"] == 0

            # Step 2: 审批通过
            approve_res = await client.post(
                f"/api/v1/workspace/plans/{run_id}/approve",
                headers=headers,
            )
            assert approve_res.status_code == 200, approve_res.text
            approve_data = approve_res.json()["data"]
            assert approve_data["status"] == "completed"
            assert approve_data["plan"]["tasks_count"] > 0

            # 验证任务已创建
            tasks_res2 = await client.get("/api/v1/workspace/tasks", headers=headers)
            assert tasks_res2.status_code == 200
            assert tasks_res2.json()["data"]["total"] > 0

            # 验证学习路径已创建
            paths_res = await client.get("/api/v1/paths", headers=headers)
            assert paths_res.status_code == 200
            assert len(paths_res.json()["data"]) >= 1

            # 验证 AgentRun 状态
            runs_res = await client.get("/api/v1/traces/runs", headers=headers)
            assert runs_res.status_code == 200
            assert runs_res.json()["data"]["total"] >= 1

    finally:
        await _cleanup_users([username])


async def test_diagnose_and_plan_reject_creates_no_tasks():
    """验证 V4.1 流程：拒绝审批不创建任何任务。"""
    await _require_database()
    suffix = uuid.uuid4().hex[:10]
    username = f"v41_reject_{suffix}"

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            token = await _register(client, username)
            headers = _auth(token)

            # 诊断 + 规划预览
            res = await client.post(
                "/api/v1/workspace/diagnose-and-plan",
                headers=headers,
                params={"goal": "学习 Python"},
            )
            assert res.status_code == 200
            run_id = res.json()["data"]["run_id"]
            assert res.json()["data"]["status"] == "waiting_approval"

            # 拒绝
            reject_res = await client.post(
                f"/api/v1/workspace/plans/{run_id}/reject",
                headers=headers,
            )
            assert reject_res.status_code == 200
            assert reject_res.json()["data"]["status"] == "cancelled"

            # 验证没有任务被创建
            tasks_res = await client.get("/api/v1/workspace/tasks", headers=headers)
            assert tasks_res.json()["data"]["total"] == 0

            # 验证没有学习路径被创建
            paths_res = await client.get("/api/v1/paths", headers=headers)
            assert len(paths_res.json()["data"]) == 0

    finally:
        await _cleanup_users([username])


async def test_task_completion():
    """验证任务完成接口。"""
    await _require_database()
    suffix = uuid.uuid4().hex[:10]
    username = f"v41_task_{suffix}"

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            token = await _register(client, username)
            headers = _auth(token)

            # 创建路径和任务（通过 approve 流程）
            res = await client.post(
                "/api/v1/workspace/diagnose-and-plan",
                headers=headers,
                params={"goal": "学习 Python"},
            )
            run_id = res.json()["data"]["run_id"]
            await client.post(f"/api/v1/workspace/plans/{run_id}/approve", headers=headers)

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
