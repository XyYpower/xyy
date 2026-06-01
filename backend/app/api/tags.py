from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.note import Tag
from app.schemas.note import TagOut
from app.utils.response import success

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get("")
async def list_tags(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Tag).order_by(Tag.name))
    tags = result.scalars().all()
    return success([TagOut.model_validate(t) for t in tags])
