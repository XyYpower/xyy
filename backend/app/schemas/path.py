import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class PathGenerateRequest(BaseModel):
    goal: str = Field(..., min_length=2, max_length=200)


class LearningPathOut(BaseModel):
    id: uuid.UUID
    name: str
    description: str
    modules: list[dict[str, Any]]
    created_at: datetime

    model_config = {"from_attributes": True}
