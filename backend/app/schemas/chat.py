import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ConversationCreate(BaseModel):
    note_id: uuid.UUID | None = None


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=4000)


class MessageOut(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    sources: list[dict] | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationOut(BaseModel):
    id: uuid.UUID
    title: str
    note_id: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime
    messages: list[MessageOut] = Field(default_factory=list)

    model_config = {"from_attributes": True}
