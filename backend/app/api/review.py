import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.review import ReviewCardOut, ReviewCardUpdate, ReviewStats, ReviewSubmitRequest
from app.services import review_service
from app.utils.deps import get_current_user
from app.utils.response import success

router = APIRouter(prefix="/review", tags=["review"])


@router.get("/today")
async def today(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    cards = await review_service.get_today_cards(db, current_user.id)
    return success([ReviewCardOut.model_validate(card) for card in cards])


@router.get("/cards/{note_id}")
async def cards(note_id: uuid.UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    items = await review_service.get_cards_for_note(db, current_user.id, note_id)
    return success([ReviewCardOut.model_validate(card) for card in items])


@router.post("/submit")
async def submit(data: ReviewSubmitRequest, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    card = await review_service.submit_review(db, current_user.id, data.card_id, data.quality)
    return success(ReviewCardOut.model_validate(card))


@router.get("/stats")
async def stats(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return success(ReviewStats(**await review_service.get_review_stats(db, current_user.id)))


@router.post("/generate/{note_id}")
async def generate(note_id: uuid.UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    cards = await review_service.generate_cards_for_note(db, current_user.id, note_id)
    return success([ReviewCardOut.model_validate(card) for card in cards])


@router.put("/cards/{card_id}")
async def update_card(
    card_id: uuid.UUID,
    data: ReviewCardUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    card = await review_service.edit_card(db, current_user.id, card_id, data.question, data.answer)
    return success(ReviewCardOut.model_validate(card))


@router.post("/cards/{card_id}/flag")
async def flag_card(card_id: uuid.UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    card = await review_service.flag_card(db, current_user.id, card_id)
    return success(ReviewCardOut.model_validate(card))

