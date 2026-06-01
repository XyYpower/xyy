import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.common import PageResult
from app.schemas.note import NoteCreate, NoteUpdate, NoteOut, NoteListItem
from app.services import note_service
from app.utils.deps import get_current_user
from app.utils.response import success

router = APIRouter(prefix="/notes", tags=["notes"])


@router.get("")
async def list_notes(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = None,
    category_id: uuid.UUID | None = None,
    tag_id: uuid.UUID | None = None,
    mastery_level: int | None = Query(None, ge=0, le=2),
    source_type: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    notes, total = await note_service.get_notes(
        db,
        current_user.id,
        page,
        page_size,
        keyword,
        category_id,
        tag_id,
        mastery_level,
        source_type,
    )
    return success(PageResult(
        items=[NoteListItem.model_validate(n) for n in notes],
        total=total,
        page=page,
        page_size=page_size,
    ))


@router.get("/{note_id}")
async def get_note(
    note_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    note = await note_service.get_note(db, note_id, current_user.id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return success(NoteOut.model_validate(note))


@router.post("")
async def create_note(
    data: NoteCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    note = await note_service.create_note(db, data, current_user.id)
    return success(NoteOut.model_validate(note))


@router.put("/{note_id}")
async def update_note(
    note_id: uuid.UUID,
    data: NoteUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    note = await note_service.get_note(db, note_id, current_user.id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    updated = await note_service.update_note(db, note, data)
    return success(NoteOut.model_validate(updated))


@router.delete("/{note_id}")
async def delete_note(
    note_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    note = await note_service.get_note(db, note_id, current_user.id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    await note_service.delete_note(db, note)
    return success(message="Deleted")
