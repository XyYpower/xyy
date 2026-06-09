import uuid
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError
from sqlalchemy import delete, select, text

from app.database import async_session
from app.models.path import LearningPath
from app.schemas.path import LearningPathOut
from app.models.user import User
from app.services import path_service


pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _require_database() -> None:
    try:
        async with async_session() as session:
            await session.execute(text("select 1"))
    except Exception as exc:
        pytest.skip(f"database is not available for path service test: {exc}")


async def test_generate_learning_path_uses_fallback_without_api_key(monkeypatch):
    await _require_database()
    username = f"path_user_{uuid.uuid4().hex[:10]}"

    class NoKeyLLM:
        api_key = ""
        provider = "deepseek"

    monkeypatch.setattr(path_service, "get_llm", lambda: NoKeyLLM())

    try:
        async with async_session() as session:
            user = User(username=username, password_hash="hash")
            session.add(user)
            await session.commit()
            await session.refresh(user)

            path = await path_service.generate_learning_path(session, user.id, "后端面试")
            await session.commit()

            assert path.name
            assert path.modules_json
            assert all("topics" in module for module in path.modules_json)

            paths = await path_service.get_paths(session, user.id)
            assert len(paths) == 1
            assert paths[0].id == path.id
    finally:
        async with async_session() as session:
            result = await session.execute(select(User.id).where(User.username == username))
            user_id = result.scalar_one_or_none()
            if user_id:
                await session.execute(delete(User).where(User.id == user_id))
                await session.commit()


async def test_parse_learning_path_from_llm_json(monkeypatch):
    class WorkingLLM:
        api_key = "configured"
        provider = "deepseek"

        async def chat_json(self, messages):
            return (
                '{"name":"后端路线","description":"面试准备",'
                '"modules":[{"name":"数据库","topics":["索引","事务"],"priority":1}]}'
            )

    monkeypatch.setattr(path_service, "get_llm", lambda: WorkingLLM())

    payload = await path_service.generate_path_payload("后端面试")

    assert payload["name"] == "后端路线"
    assert payload["modules"][0]["topics"] == ["索引", "事务"]


async def test_parse_learning_path_preserves_zero_priority(monkeypatch):
    class WorkingLLM:
        api_key = "configured"
        provider = "deepseek"

        async def chat_json(self, messages):
            return (
                '{"name":"后端路线","description":"面试准备",'
                '"modules":[{"name":"数据库","topics":["索引","事务"],"priority":0}]}'
            )

    monkeypatch.setattr(path_service, "get_llm", lambda: WorkingLLM())

    payload = await path_service.generate_path_payload("后端面试")

    assert payload["modules"][0]["priority"] == 0


async def test_learning_path_output_rejects_invalid_modules():
    with pytest.raises(ValidationError):
        LearningPathOut.model_validate(
            {
                "id": uuid.uuid4(),
                "name": "坏路径",
                "description": "topics 不是数组",
                "modules": [{"name": "数据库", "topics": "索引,事务", "priority": 1}],
                "created_at": datetime.now(UTC),
            }
        )
