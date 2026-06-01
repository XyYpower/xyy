import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ReviewCardOut(BaseModel):
    id: uuid.UUID
    note_id: uuid.UUID
    card_type: str
    question: str
    answer: str
    next_review_at: datetime | None = None
    ease_factor: float
    interval_days: int
    review_count: int
    is_user_edited: bool
    is_flagged: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ReviewSubmitRequest(BaseModel):
    card_id: uuid.UUID
    quality: int = Field(..., ge=0, le=5)


class ReviewCardUpdate(BaseModel):
    question: str = Field(..., min_length=1)
    answer: str = Field(..., min_length=1)


class ReviewStats(BaseModel):
    total_cards: int
    due_today: int
    mastered_count: int
    learning_count: int
    new_count: int

