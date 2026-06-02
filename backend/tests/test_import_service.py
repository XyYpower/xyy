import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy import delete, select, text

from app.database import async_session
from app.models.chat import NoteChunk
from app.models.import_job import ExtractionDraft, ImportJob
from app.models.note import Note
from app.models.review import ReviewCard
from app.models.user import User
from app.services import import_service


pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _require_database() -> None:
    try:
        async with async_session() as session:
            await session.execute(text("select 1"))
    except Exception as exc:
        pytest.skip(f"database is not available for import service test: {exc}")


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


async def test_import_service_creates_drafts_and_confirms_notes(monkeypatch):
    await _require_database()
    username = f"import_user_{uuid.uuid4().hex[:10]}"

    async def fake_extract(text: str):
        return [
            {"title": "缓存穿透", "content": "缓存穿透是查询不存在的数据。"},
            {"title": "布隆过滤器", "content": "布隆过滤器可以拦截不存在的 key。"},
        ]

    monkeypatch.setattr(import_service, "extract_knowledge_points", fake_extract)
    async def fake_embed(text_value: str):
        return [0.01] * 1536

    monkeypatch.setattr(import_service.note_service.embedding, "embed_text", fake_embed)

    try:
        user = await _create_user(username)
        async with async_session() as session:
            job = await import_service.create_import_job(
                session,
                user.id,
                source_type="text",
                source_text="缓存穿透和布隆过滤器。",
            )
            await session.commit()
            job_id = job.id

        async with async_session() as session:
            drafts = await import_service.get_drafts(session, user.id, job_id)
            assert len(drafts) == 2
            assert drafts[0].is_selected is True

            updated = await import_service.update_draft(
                session,
                user.id,
                drafts[1].id,
                title="布隆过滤器方案",
                content=None,
                is_selected=False,
            )
            assert updated.title == "布隆过滤器方案"
            assert updated.is_selected is False

            notes = await import_service.confirm_import(session, user.id, job_id)
            await session.commit()
            assert len(notes) == 1
            assert notes[0].source_type == "imported"

        async with async_session() as session:
            job = await session.get(ImportJob, job_id)
            assert job.status == "confirmed"
            note_count = (await session.execute(select(Note).where(Note.user_id == user.id))).scalars().all()
            assert len(note_count) == 1
            cards = (await session.execute(select(ReviewCard).join(ReviewCard.note).where(Note.user_id == user.id))).scalars().all()
            assert cards == []
            chunks = (
                await session.execute(select(NoteChunk).join(Note).where(Note.user_id == user.id))
            ).scalars().all()
            assert len(chunks) == 1
            confirmed_drafts = (
                await session.execute(select(ExtractionDraft).where(ExtractionDraft.import_job_id == job_id))
            ).scalars().all()
            assert sum(1 for draft in confirmed_drafts if draft.note_id) == 1
    finally:
        await _cleanup_user(username)


@pytest.mark.parametrize(
    "url",
    [
        "ftp://example.com/article",
        "http://127.0.0.1:1/admin",
        "http://localhost:1/admin",
    ],
)
async def test_fetch_url_text_rejects_unsafe_targets(url: str):
    with pytest.raises(HTTPException) as exc_info:
        await import_service.fetch_url_text(url)

    assert exc_info.value.status_code == 400


async def test_confirm_import_does_not_generate_review_cards_inline(monkeypatch):
    await _require_database()
    username = f"import_no_inline_{uuid.uuid4().hex[:10]}"

    async def explode_if_called(db, user_id, note_id):
        raise AssertionError("confirm_import should not call LLM card generation inline")

    monkeypatch.setattr(import_service.review_service, "generate_cards_for_note", explode_if_called)
    async def fake_embed(text_value: str):
        return [0.01] * 1536

    monkeypatch.setattr(import_service.note_service.embedding, "embed_text", fake_embed)

    try:
        user = await _create_user(username)
        async with async_session() as session:
            job = ImportJob(
                user_id=user.id,
                source_type="text",
                source_text="缓存穿透是查询不存在的数据。",
                status="draft",
            )
            session.add(job)
            await session.flush()
            draft = ExtractionDraft(import_job_id=job.id, title="缓存穿透", content="查询不存在的数据。")
            session.add(draft)
            await session.commit()
            job_id = job.id

        async with async_session() as session:
            notes = await import_service.confirm_import(session, user.id, job_id)
            await session.commit()
            assert len(notes) == 1

        async with async_session() as session:
            cards = (
                await session.execute(select(ReviewCard).join(ReviewCard.note).where(Note.user_id == user.id))
            ).scalars().all()
            assert cards == []
    finally:
        await _cleanup_user(username)
