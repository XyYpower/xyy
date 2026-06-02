from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.note import TagOut
from app.services import note_service
from app.utils.deps import get_current_user
from app.utils.response import success

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get("")
async def list_tags(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tags = await note_service.get_tags_for_user(db, current_user.id)
    return success([TagOut.model_validate(t) for t in tags])
