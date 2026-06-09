import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.note import CategoryCreate, CategoryOut, CategoryUpdate
from app.services import note_service
from app.utils.deps import get_current_user
from app.utils.response import success

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("")
async def list_categories(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    categories = await note_service.get_categories_for_user(db, current_user.id)
    return success([CategoryOut.model_validate(c) for c in categories])


@router.post("")
async def create_category(
    data: CategoryCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    category = await note_service.create_category(db, current_user.id, data)
    return success(CategoryOut.model_validate(category))


@router.put("/{category_id}")
async def update_category(
    category_id: uuid.UUID,
    data: CategoryUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    category = await note_service.update_category(db, current_user.id, category_id, data)
    return success(CategoryOut.model_validate(category))


@router.delete("/{category_id}")
async def delete_category(
    category_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await note_service.delete_category(db, current_user.id, category_id)
    return success(message="Deleted")
