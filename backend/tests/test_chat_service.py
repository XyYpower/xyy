import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import delete, select, text
from sqlalchemy import inspect

from app.database import async_session
from app.models.chat import Conversation, Message
from app.models.user import User
from app.services import chat_service


pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _require_database() -> None:
    try:
        async with async_session() as session:
            await session.execute(text("select 1"))
    except Exception as exc:
        pytest.skip(f"database is not available for chat service test: {exc}")


async def _create_user(username: str) -> User:
    async with async_session() as session:
        user = User(username=username, password_hash="hash")
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


async def _cleanup_users(usernames: list[str]) -> None:
    async with async_session() as session:
        result = await session.execute(select(User.id).where(User.username.in_(usernames)))
        user_ids = result.scalars().all()
        if user_ids:
            await session.execute(delete(User).where(User.id.in_(user_ids)))
            await session.commit()


async def test_conversation_crud_is_user_scoped():
    await _require_database()
    suffix = uuid.uuid4().hex[:10]
    owner_username = f"chat_owner_{suffix}"
    other_username = f"chat_other_{suffix}"

    try:
        owner = await _create_user(owner_username)
        other = await _create_user(other_username)

        async with async_session() as session:
            conversation = await chat_service.create_conversation(session, owner.id)
            await session.commit()
            conversation_id = conversation.id

        async with async_session() as session:
            owner_conversations = await chat_service.get_conversations(session, owner.id)
            assert [item.id for item in owner_conversations] == [conversation_id]

            other_conversations = await chat_service.get_conversations(session, other.id)
            assert other_conversations == []

            assert await chat_service.get_conversation(session, owner.id, conversation_id)
            assert await chat_service.get_conversation(session, other.id, conversation_id) is None

            deleted = await chat_service.delete_conversation(session, other.id, conversation_id)
            assert deleted is False
            deleted = await chat_service.delete_conversation(session, owner.id, conversation_id)
            assert deleted is True
            await session.commit()

        async with async_session() as session:
            assert await session.get(Conversation, conversation_id) is None
    finally:
        await _cleanup_users([owner_username, other_username])


async def test_chat_stream_persists_messages_and_sources(monkeypatch):
    await _require_database()
    username = f"chat_stream_{uuid.uuid4().hex[:10]}"
    source_note_id = uuid.uuid4()
    contexts = [
        {
            "note_id": source_note_id,
            "note_title": "Redis 缓存穿透",
            "chunk_text": "布隆过滤器可以拦截不存在的 key。",
            "similarity": 0.91,
        }
    ]

    async def fake_search(*args, **kwargs):
        return contexts

    class FakeLLM:
        api_key = "test-key"

        async def chat_stream(self, messages):
            yield "布隆过滤器"
            yield "可以提前拦截。"

    monkeypatch.setattr(chat_service.retrieval, "search_similar", fake_search)
    monkeypatch.setattr(chat_service, "get_llm", lambda **_: FakeLLM())

    try:
        user = await _create_user(username)

        async with async_session() as session:
            conversation = await chat_service.create_conversation(session, user.id)
            chunks = [
                chunk async for chunk in chat_service.chat_stream(session, user.id, conversation.id, "什么是缓存穿透？")
            ]
            await session.commit()
            conversation_id = conversation.id

        assert chunks == ["布隆过滤器", "可以提前拦截。"]

        async with async_session() as session:
            messages = (
                await session.execute(
                    select(Message)
                    .where(Message.conversation_id == conversation_id)
                    .order_by(Message.created_at, Message.role)
                )
            ).scalars().all()

            assert [message.role for message in messages] == ["assistant", "user"] or [
                message.role for message in messages
            ] == ["user", "assistant"]
            user_message = next(message for message in messages if message.role == "user")
            assistant_message = next(message for message in messages if message.role == "assistant")
            assert user_message.content == "什么是缓存穿透？"
            assert assistant_message.content == "布隆过滤器可以提前拦截。"
            assert assistant_message.sources == [{"note_id": str(source_note_id), "title": "Redis 缓存穿透"}]
    finally:
        await _cleanup_users([username])


async def test_chat_stream_uses_fallback_without_api_key(monkeypatch):
    await _require_database()
    username = f"chat_fallback_{uuid.uuid4().hex[:10]}"

    async def fake_search(*args, **kwargs):
        return []

    class NoKeyLLM:
        api_key = ""

    monkeypatch.setattr(chat_service.retrieval, "search_similar", fake_search)
    monkeypatch.setattr(chat_service, "get_llm", lambda **_: NoKeyLLM())

    try:
        user = await _create_user(username)

        async with async_session() as session:
            conversation = await chat_service.create_conversation(session, user.id)
            chunks = [chunk async for chunk in chat_service.chat_stream(session, user.id, conversation.id, "不存在的问题")]
            await session.commit()

        assert chunks
        assert "LLM" in "".join(chunks)
    finally:
        await _cleanup_users([username])


async def test_chat_stream_does_not_mix_partial_llm_output_with_fallback(monkeypatch):
    await _require_database()
    username = f"chat_partial_{uuid.uuid4().hex[:10]}"

    async def fake_search(*args, **kwargs):
        return []

    class BrokenLLM:
        api_key = "test-key"

        async def chat_stream(self, messages):
            yield "半句回答"
            raise RuntimeError("stream interrupted")

    monkeypatch.setattr(chat_service.retrieval, "search_similar", fake_search)
    monkeypatch.setattr(chat_service, "get_llm", lambda **_: BrokenLLM())

    try:
        user = await _create_user(username)

        async with async_session() as session:
            conversation = await chat_service.create_conversation(session, user.id)
            chunks = [
                chunk async for chunk in chat_service.chat_stream(session, user.id, conversation.id, "会失败的问题")
            ]
            await session.commit()
            conversation_id = conversation.id

        assert chunks == ["半句回答"]

        async with async_session() as session:
            assistant = (
                await session.execute(
                    select(Message).where(Message.conversation_id == conversation_id, Message.role == "assistant")
                )
            ).scalar_one()
            assert assistant.content == "半句回答"
    finally:
        await _cleanup_users([username])


async def test_get_conversations_does_not_eager_load_messages():
    await _require_database()
    username = f"chat_list_{uuid.uuid4().hex[:10]}"

    try:
        user = await _create_user(username)

        async with async_session() as session:
            conversation = await chat_service.create_conversation(session, user.id)
            db_message = Message(conversation_id=conversation.id, role="user", content="历史消息")
            session.add(db_message)
            await session.commit()

        async with async_session() as session:
            conversations = await chat_service.get_conversations(session, user.id)
            assert conversations
            assert "messages" in inspect(conversations[0]).unloaded
    finally:
        await _cleanup_users([username])


async def test_chat_stream_updates_conversation_updated_at(monkeypatch):
    await _require_database()
    username = f"chat_updated_{uuid.uuid4().hex[:10]}"

    async def fake_search(*args, **kwargs):
        return []

    class NoKeyLLM:
        api_key = ""

    monkeypatch.setattr(chat_service.retrieval, "search_similar", fake_search)
    monkeypatch.setattr(chat_service, "get_llm", lambda **_: NoKeyLLM())

    try:
        user = await _create_user(username)
        old_time = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=2)

        async with async_session() as session:
            conversation = await chat_service.create_conversation(session, user.id)
            conversation.updated_at = old_time
            await session.commit()
            conversation_id = conversation.id

        async with async_session() as session:
            _ = [chunk async for chunk in chat_service.chat_stream(session, user.id, conversation_id, "更新时间")]
            await session.commit()

        async with async_session() as session:
            conversation = await session.get(Conversation, conversation_id)
            assert conversation.updated_at > old_time
    finally:
        await _cleanup_users([username])
