"""V3.1 Agent Runtime + Trace 基础集成测试。"""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select, text

from app.database import async_session
from app.main import app
from app.models.user import User
from app.models.agent import AgentRun, AgentStep, ToolCall, AICallLog

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _require_database() -> None:
    try:
        async with async_session() as session:
            await session.execute(text("select 1"))
    except Exception as exc:
        pytest.skip(f"database is not available for V3.1 agent test: {exc}")


async def _cleanup_users(usernames: list[str]) -> None:
    async with async_session() as session:
        result = await session.execute(select(User.id).where(User.username.in_(usernames)))
        user_ids = result.scalars().all()
        if user_ids:
            await session.execute(delete(AICallLog).where(AICallLog.user_id.in_(user_ids)))
            await session.execute(delete(ToolCall).where(ToolCall.run_id.in_(
                select(AgentRun.id).where(AgentRun.user_id.in_(user_ids))
            )))
            await session.execute(delete(AgentStep).where(AgentStep.run_id.in_(
                select(AgentRun.id).where(AgentRun.user_id.in_(user_ids))
            )))
            await session.execute(delete(AgentRun).where(AgentRun.user_id.in_(user_ids)))
            await session.execute(delete(User).where(User.id.in_(user_ids)))
            await session.commit()


async def _register(client: AsyncClient, username: str, password: str = "secret123") -> str:
    response = await client.post("/api/v1/auth/register", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["data"]["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def test_agent_runtime_lifecycle_and_trace_lab_api():
    """验证 AgentRun 生命周期 + Trace Lab API。"""
    await _require_database()
    suffix = uuid.uuid4().hex[:10]
    username = f"v31_trace_{suffix}"

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            token = await _register(client, username)
            headers = _auth(token)

            # 直接通过 runtime 模块创建运行记录
            from app.agents import runtime
            async with async_session() as db:
                run = await runtime.start_run(db, uuid.UUID(
                    (await client.get("/api/v1/auth/me", headers=headers)).json()["data"]["id"]
                ), "diagnosis", goal="测试目标", input_data={"test": True})

                step = await runtime.create_step(
                    db, run.id, 1, "DiagnosisAgent", "analyze_notes",
                    input_data={"keyword": "test"}
                )
                await runtime.complete_step(db, step.id, output={"found": 5}, latency_ms=120)

                await runtime.update_run_status(db, run.id, "completed",
                    output={"summary": "诊断完成"})
                await db.commit()

            # 查询运行列表
            runs_res = await client.get("/api/v1/traces/runs", headers=headers)
            assert runs_res.status_code == 200
            runs_data = runs_res.json()["data"]
            assert runs_data["total"] >= 1

            # 查询运行详情
            run_id = runs_data["items"][0]["id"]
            detail_res = await client.get(f"/api/v1/traces/runs/{run_id}", headers=headers)
            assert detail_res.status_code == 200
            detail = detail_res.json()["data"]
            assert detail["run_type"] == "diagnosis"
            assert detail["status"] == "completed"
            assert len(detail["steps"]) == 1
            assert detail["steps"][0]["status"] == "completed"

            # 查询统计
            stats_res = await client.get("/api/v1/traces/stats", headers=headers)
            assert stats_res.status_code == 200
            stats = stats_res.json()["data"]
            assert stats["total_runs"] >= 1
            assert stats["completed_runs"] >= 1
            assert stats["success_rate"] > 0

            # 查询 AI 日志
            logs_res = await client.get("/api/v1/traces/ai-logs", headers=headers)
            assert logs_res.status_code == 200

    finally:
        await _cleanup_users([username])


async def test_tool_registry_register_and_execute():
    """验证 ToolRegistry 注册和执行。"""
    from app.agents.registry import ToolRegistry, ToolDef, ToolResult

    reg = ToolRegistry()

    async def mock_search(db, user_id, keyword=""):
        return {"results": [{"title": "test"}]}

    reg.register(ToolDef(
        name="notes.search",
        description="搜索知识点",
        requires_approval=False,
        fn=mock_search,
    ))

    tools = reg.list_tools()
    assert len(tools) == 1
    assert tools[0].name == "notes.search"

    # 未知工具返回 ok=False
    result = await reg.execute("unknown.tool", {}, None, uuid.uuid4())
    assert not result.ok

    # 已注册工具返回 ok=True
    result = await reg.execute("notes.search", {"keyword": "test"}, None, uuid.uuid4())
    assert result.ok


async def test_ai_call_log_records_llm_usage():
    """验证 ai_call_logs 能记录 LLM 调用。"""
    await _require_database()
    suffix = uuid.uuid4().hex[:10]
    username = f"v31_log_{suffix}"

    try:
        async with async_session() as db:
            from app.agents.traces import record_llm_call_standalone
            user = (await db.execute(select(User).where(User.username == username))).scalar_one_or_none()
            if not user:
                user = User(username=username, password_hash="test")
                db.add(user)
                await db.flush()
            user_id = user.id

            log = await record_llm_call_standalone(
                db, user_id, "deepseek", "deepseek-chat", "chat",
                latency_ms=500, status="success",
            )
            await db.commit()

            # 验证记录存在
            async with async_session() as verify_db:
                result = await verify_db.execute(
                    select(AICallLog).where(AICallLog.user_id == user_id)
                )
                records = result.scalars().all()
                assert len(records) >= 1
                assert records[0].provider == "deepseek"
                assert records[0].purpose == "chat"
                assert records[0].latency_ms == 500
    finally:
        await _cleanup_users([username])
