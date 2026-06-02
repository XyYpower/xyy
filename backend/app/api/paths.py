import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.path import LearningPathOut, PathGenerateRequest
from app.services import path_service
from app.utils.deps import get_current_user
from app.utils.response import success

router = APIRouter(prefix="/paths", tags=["paths"])


@router.post("/generate")
async def generate(
    data: PathGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    path = await path_service.generate_learning_path(db, current_user.id, data.goal)
    return success(LearningPathOut.model_validate(path))


@router.get("")
async def list_paths(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    paths = await path_service.get_paths(db, current_user.id)
    return success([LearningPathOut.model_validate(path) for path in paths])


@router.get("/{path_id}")
async def get_path(
    path_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    path = await path_service.get_path(db, current_user.id, path_id)
    return success(LearningPathOut.model_validate(path))
