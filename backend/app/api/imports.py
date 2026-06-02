import uuid

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.import_job import (
    DraftUpdateRequest,
    ExtractionDraftOut,
    ImportCodeRequest,
    ImportJobOut,
    ImportResultOut,
    ImportTextRequest,
    ImportUrlRequest,
)
from app.schemas.note import NoteOut
from app.services import import_service, review_service
from app.utils.deps import get_current_user
from app.utils.response import success

router = APIRouter(prefix="/import", tags=["import"])


@router.post("/text")
async def import_text(
    data: ImportTextRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    job = await import_service.create_import_job(db, current_user.id, "text", data.text, data.source_url)
    drafts = await import_service.get_drafts(db, current_user.id, job.id)
    return success(ImportResultOut(job=ImportJobOut.model_validate(job), drafts=[ExtractionDraftOut.model_validate(d) for d in drafts]))


@router.post("/url")
async def import_url(
    data: ImportUrlRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    text = await import_service.fetch_url_text(data.url)
    job = await import_service.create_import_job(db, current_user.id, "url", text, data.url)
    drafts = await import_service.get_drafts(db, current_user.id, job.id)
    return success(ImportResultOut(job=ImportJobOut.model_validate(job), drafts=[ExtractionDraftOut.model_validate(d) for d in drafts]))


@router.post("/code")
async def import_code(
    data: ImportCodeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    source_text = f"语言：{data.language or 'unknown'}\n\n{data.code}"
    job = await import_service.create_import_job(db, current_user.id, "code", source_text)
    drafts = await import_service.get_drafts(db, current_user.id, job.id)
    return success(ImportResultOut(job=ImportJobOut.model_validate(job), drafts=[ExtractionDraftOut.model_validate(d) for d in drafts]))


@router.get("/jobs")
async def jobs(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    items = await import_service.get_import_jobs(db, current_user.id)
    return success([ImportJobOut.model_validate(job) for job in items])


@router.get("/jobs/{job_id}/drafts")
async def drafts(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    items = await import_service.get_drafts(db, current_user.id, job_id)
    return success([ExtractionDraftOut.model_validate(draft) for draft in items])


@router.put("/drafts/{draft_id}")
async def update_draft(
    draft_id: uuid.UUID,
    data: DraftUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    draft = await import_service.update_draft(
        db,
        current_user.id,
        draft_id,
        data.title,
        data.content,
        data.is_selected,
    )
    return success(ExtractionDraftOut.model_validate(draft))


@router.post("/jobs/{job_id}/confirm")
async def confirm(
    job_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    notes = await import_service.confirm_import(db, current_user.id, job_id)
    await db.commit()
    for note in notes:
        background_tasks.add_task(review_service.generate_cards_for_note_task, current_user.id, note.id)
    return success([NoteOut.model_validate(note) for note in notes])
