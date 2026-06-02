import json

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.services import export_service
from app.utils.deps import get_current_user

router = APIRouter(prefix="/export", tags=["export"])


@router.get("/json")
async def export_json(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    payload = await export_service.export_json(db, current_user.id)
    return Response(
        content=json.dumps(payload, ensure_ascii=False, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="knowbase-export.json"'},
    )


@router.get("/markdown")
async def export_markdown(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    content = await export_service.export_markdown(db, current_user.id)
    return Response(
        content=content,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="knowbase-notes.md"'},
    )


@router.get("/anki")
async def export_anki(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    content = await export_service.export_anki_csv(db, current_user.id)
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="knowbase-anki.csv"'},
    )
