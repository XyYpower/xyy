import re
import uuid
from html import unescape

import httpx
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.import_job import ExtractionDraft, ImportJob
from app.models.note import Note
from app.rag.extractor import extract_knowledge_points
from app.services import review_service


async def create_import_job(
    db: AsyncSession,
    user_id: uuid.UUID,
    source_type: str,
    source_text: str,
    source_url: str | None = None,
) -> ImportJob:
    job = ImportJob(
        user_id=user_id,
        source_type=source_type,
        source_url=source_url,
        source_text=source_text,
        status="pending",
    )
    db.add(job)
    await db.flush()

    job.status = "processing"
    try:
        items = await extract_knowledge_points(source_text)
        drafts = [
            ExtractionDraft(import_job_id=job.id, title=item["title"], content=item["content"])
            for item in items
        ]
        db.add_all(drafts)
        job.status = "draft"
        await db.flush()
        await db.refresh(job)
        return job
    except Exception as exc:
        job.status = "failed"
        job.error_message = str(exc)
        await db.flush()
        await db.refresh(job)
        return job


async def get_import_jobs(db: AsyncSession, user_id: uuid.UUID) -> list[ImportJob]:
    result = await db.execute(
        select(ImportJob)
        .where(ImportJob.user_id == user_id)
        .order_by(ImportJob.created_at.desc())
    )
    return result.scalars().all()


async def get_import_job(db: AsyncSession, user_id: uuid.UUID, job_id: uuid.UUID) -> ImportJob | None:
    result = await db.execute(
        select(ImportJob)
        .options(selectinload(ImportJob.drafts))
        .where(ImportJob.id == job_id, ImportJob.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def get_drafts(db: AsyncSession, user_id: uuid.UUID, job_id: uuid.UUID) -> list[ExtractionDraft]:
    job = await get_import_job(db, user_id, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Import job not found")
    return sorted(job.drafts, key=lambda draft: draft.created_at)


async def update_draft(
    db: AsyncSession,
    user_id: uuid.UUID,
    draft_id: uuid.UUID,
    title: str | None = None,
    content: str | None = None,
    is_selected: bool | None = None,
) -> ExtractionDraft:
    draft = await _get_owned_draft(db, user_id, draft_id)
    if title is not None:
        draft.title = title
    if content is not None:
        draft.content = content
    if is_selected is not None:
        draft.is_selected = is_selected
    await db.flush()
    await db.refresh(draft)
    return draft


async def confirm_import(db: AsyncSession, user_id: uuid.UUID, job_id: uuid.UUID) -> list[Note]:
    job = await get_import_job(db, user_id, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Import job not found")
    if job.status != "draft":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Import job is not ready to confirm")

    selected_drafts = [draft for draft in job.drafts if draft.is_selected and draft.note_id is None]
    notes: list[Note] = []
    for draft in selected_drafts:
        note = Note(
            user_id=user_id,
            title=draft.title,
            content=draft.content,
            source_type="imported",
            source_url=job.source_url,
        )
        db.add(note)
        await db.flush()
        await db.refresh(note)
        draft.note_id = note.id
        notes.append(note)
        await review_service.generate_cards_for_note(db, user_id, note.id)

    job.status = "confirmed"
    await db.flush()
    return notes


async def fetch_url_text(url: str) -> str:
    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        response = await client.get(url, headers={"User-Agent": "KnowBase/1.0"})
        response.raise_for_status()
    html = response.text
    html = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", html)
    text = unescape(re.sub(r"\s+", " ", text)).strip()
    return text[:8000]


async def _get_owned_draft(db: AsyncSession, user_id: uuid.UUID, draft_id: uuid.UUID) -> ExtractionDraft:
    result = await db.execute(
        select(ExtractionDraft)
        .join(ExtractionDraft.import_job)
        .where(ExtractionDraft.id == draft_id, ImportJob.user_id == user_id)
    )
    draft = result.scalar_one_or_none()
    if not draft:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Extraction draft not found")
    return draft
