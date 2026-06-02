import uuid

import pytest
from sqlalchemy import delete, select, text

from app.database import async_session
from app.models.chat import NoteChunk
from app.models.note import Note
from app.models.user import User
from app.rag import embedding, retrieval
from app.schemas.note import NoteCreate
from app.services import note_service


pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _require_database() -> None:
    try:
        async with async_session() as session:
            await session.execute(text("select 1"))
    except Exception as exc:
        pytest.skip(f"database is not available for embedding retrieval test: {exc}")


async def _create_user(username: str) -> User:
    async with async_session() as session:
        user = User(username=username, password_hash="hash")
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


async def _cleanup_user(username: str) -> None:
    async with async_session() as session:
        result = await session.execute(select(User.id).where(User.username == username))
        user_id = result.scalar_one_or_none()
        if user_id:
            await session.execute(delete(User).where(User.id == user_id))
            await session.commit()


async def test_fallback_embedding_is_deterministic_1536_dimensions(monkeypatch):
    client = embedding.EmbeddingClient("deepseek", "", "https://example.com", "fallback")
    monkeypatch.setattr(embedding, "get_embedding_client", lambda: client)

    first = await embedding.embed_text("Redis 缓存穿透")
    second = await embedding.embed_text("Redis 缓存穿透")

    assert len(first) == 1536
    assert first == second
    assert any(value != 0 for value in first)


async def test_split_text_keeps_short_text_and_splits_paragraphs():
    assert note_service.split_note_text("短知识点") == ["短知识点"]

    long_text = "第一段" * 120 + "\n\n" + "第二段" * 120
    chunks = note_service.split_note_text(long_text, max_chunk_size=500)

    assert len(chunks) == 2
    assert chunks[0].startswith("第一段")
    assert chunks[1].startswith("第二段")


async def test_create_note_generates_chunks_and_search_is_user_scoped(monkeypatch):
    await _require_database()
    owner_username = f"chunk_owner_{uuid.uuid4().hex[:10]}"
    other_username = f"chunk_other_{uuid.uuid4().hex[:10]}"

    async def fake_embed(text_value: str):
        return [0.01] * 1536

    monkeypatch.setattr(note_service.embedding, "embed_text", fake_embed)
    monkeypatch.setattr(retrieval.embedding, "embed_text", fake_embed)

    try:
        owner = await _create_user(owner_username)
        other = await _create_user(other_username)
        async with async_session() as session:
            owner_note = await note_service.create_note(
                session,
                NoteCreate(title="Redis 缓存穿透", content="布隆过滤器可以拦截不存在的 key。"),
                owner.id,
            )
            await note_service.create_note(
                session,
                NoteCreate(title="JWT 认证", content="Refresh Token 用来刷新 Access Token。"),
                other.id,
            )
            await session.commit()
            owner_note_id = owner_note.id

        async with async_session() as session:
            chunks = (
                await session.execute(select(NoteChunk).join(Note).where(Note.user_id == owner.id))
            ).scalars().all()
            assert len(chunks) == 1
            assert chunks[0].note_id == owner_note_id
            assert chunks[0].content_hash

            results = await retrieval.search_similar(session, owner.id, "缓存穿透", top_k=5)
            assert len(results) == 1
            assert results[0]["note_id"] == owner_note_id
            assert results[0]["note_title"] == "Redis 缓存穿透"

            other_results = await retrieval.search_similar(session, uuid.uuid4(), "缓存穿透", top_k=5)
            assert other_results == []
    finally:
        await _cleanup_user(owner_username)
        await _cleanup_user(other_username)
