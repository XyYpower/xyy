from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.note import Category
from app.models.user import User
from app.schemas.note import CategoryOut
from app.utils.deps import get_current_user
from app.utils.response import success

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("")
async def list_categories(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ = current_user
    result = await db.execute(select(Category).order_by(Category.sort_order))
    categories = result.scalars().all()
    return success([CategoryOut.model_validate(c) for c in categories])
