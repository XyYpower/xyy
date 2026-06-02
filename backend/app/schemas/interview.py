import uuid
from datetime import datetime

from pydantic import BaseModel, Field, computed_field


class InterviewStartRequest(BaseModel):
    scope: str = Field("all", pattern="^(all|weak_points)$")
    num_questions: int = Field(5, ge=1, le=20)


class AnswerSubmitRequest(BaseModel):
    answer: str = Field(..., min_length=1)


class InterviewQuestionOut(BaseModel):
    id: uuid.UUID
    question: str
    reference_answer: str | None = None
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

    @computed_field
    @property
    def score_percent(self) -> int | None:
        if self.total_score is None or not self.questions:
            return None
        return round((self.total_score / (len(self.questions) * 10)) * 100)


class WeakPointOut(BaseModel):
    note_id: uuid.UUID
    title: str
    avg_score: float
    times_tested: int
