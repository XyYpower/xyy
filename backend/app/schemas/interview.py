import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class InterviewStartRequest(BaseModel):
    scope: str = Field("all", pattern="^(all|weak_points)$")
    num_questions: int = Field(5, ge=1, le=20)


class AnswerSubmitRequest(BaseModel):
    answer: str = Field(..., min_length=1)


class InterviewQuestionOut(BaseModel):
    id: uuid.UUID
    question: str
    user_answer: str | None = None
    ai_score: int | None = None
    ai_feedback: str | None = None
    question_order: int

    model_config = {"from_attributes": True}


class InterviewSessionOut(BaseModel):
    id: uuid.UUID
    title: str
    scope: str
    total_score: int | None = None
    summary: str | None = None
    status: str
    created_at: datetime
    finished_at: datetime | None = None
    questions: list[InterviewQuestionOut] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class WeakPointOut(BaseModel):
    note_id: uuid.UUID
    title: str
    avg_score: float
    times_tested: int
