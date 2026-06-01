from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.note import Category
from app.schemas.note import CategoryOut
from app.utils.response import success

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("")
async def list_categories(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Category).order_by(Category.sort_order))
    categories = result.scalars().all()
    return success([CategoryOut.model_validate(c) for c in categories])
