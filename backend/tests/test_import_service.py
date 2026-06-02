import uuid

import pytest
from sqlalchemy import delete, select, text

from app.database import async_session
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

    async def fake_generate_cards(db, user_id, note_id):
        cards = [
            ReviewCard(note_id=note_id, card_type="concept", question="q1", answer="a1"),
            ReviewCard(note_id=note_id, card_type="code", question="q2", answer="a2"),
            ReviewCard(note_id=note_id, card_type="scenario", question="q3", answer="a3"),
        ]
        db.add_all(cards)
        await db.flush()
        return cards

    monkeypatch.setattr(import_service, "extract_knowledge_points", fake_extract)
    monkeypatch.setattr(import_service.review_service, "generate_cards_for_note", fake_generate_cards)

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
            assert len(cards) == 3
            confirmed_drafts = (
                await session.execute(select(ExtractionDraft).where(ExtractionDraft.import_job_id == job_id))
            ).scalars().all()
            assert sum(1 for draft in confirmed_drafts if draft.note_id) == 1
    finally:
        await _cleanup_user(username)
