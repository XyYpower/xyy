import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class TagOut(BaseModel):
    id: uuid.UUID
    name: str

    model_config = {"from_attributes": True}


class CategoryOut(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None = None

    model_config = {"from_attributes": True}


class NoteCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(default="")
    summary: str | None = None
    category_id: uuid.UUID | None = None
    tag_names: list[str] = Field(default_factory=list)
    is_favorite: bool = False


class NoteUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=200)
    content: str | None = None
    summary: str | None = None
    category_id: uuid.UUID | None = None
    tag_names: list[str] | None = None
    is_favorite: bool | None = None


class NoteOut(BaseModel):
    id: uuid.UUID
    title: str
    content: str
    summary: str | None = None
    category: CategoryOut | None = None
    tags: list[TagOut] = []
    is_favorite: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class NoteListItem(BaseModel):
    id: uuid.UUID
    title: str
    summary: str | None = None
    category: CategoryOut | None = None
    tags: list[TagOut] = []
    is_favorite: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
