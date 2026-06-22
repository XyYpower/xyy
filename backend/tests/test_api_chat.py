import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select, text

from app.database import async_session
from app.main import app
from app.models.chat import Message
from app.models.user import User
from app.services import chat_service


pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _require_database() -> None:
    try:
        async with async_session() as session:
            await session.execute(text("select 1"))
    except Exception as exc:
        pytest.skip(f"database is not available for chat API test: {exc}")


async def _cleanup_users(usernames: list[str]) -> None:
    async with async_session() as session:
        result = await session.execute(select(User.id).where(User.username.in_(usernames)))
        user_ids = result.scalars().all()
        if user_ids:
            await session.execute(delete(User).where(User.id.in_(user_ids)))
            await session.commit()


async def _register(client: AsyncClient, username: str) -> str:
    response = await client.post(
        "/api/v1/auth/register",
        json={"username": username, "password": "secret123"},
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]["access_token"]


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def test_chat_api_streams_and_persists_messages(monkeypatch):
    await _require_database()
    username = f"api_chat_{uuid.uuid4().hex[:10]}"

    async def fake_search(*args, **kwargs):
        return []

    class NoKeyLLM:
        api_key = ""

    monkeypatch.setattr(chat_service.retrieval, "search_similar", fake_search)
    monkeypatch.setattr(chat_service, "get_llm", lambda **_: NoKeyLLM())

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            token = await _register(client, username)
            headers = _auth_header(token)

            create_response = await client.post("/api/v1/chat/conversations", headers=headers, json={})
            assert create_response.status_code == 200, create_response.text
            conversation_id = create_response.json()["data"]["id"]

            stream_response = await client.post(
                f"/api/v1/chat/conversations/{conversation_id}/chat",
                headers=headers,
                json={"query": "什么是 RAG？"},
            )
            assert stream_response.status_code == 200, stream_response.text
            assert "text/event-stream" in stream_response.headers["content-type"]
            assert "data: " in stream_response.text
            assert '"done": true' in stream_response.text

        async with async_session() as session:
            messages = (
                await session.execute(
                    select(Message)
                    .where(Message.conversation_id == uuid.UUID(conversation_id))
                    .order_by(Message.created_at)
                )
            ).scalars().all()
            assert [message.role for message in messages] == ["user", "assistant"]
            assert messages[0].content == "什么是 RAG？"
            assert "LLM" in messages[1].content
    finally:
        await _cleanup_users([username])
