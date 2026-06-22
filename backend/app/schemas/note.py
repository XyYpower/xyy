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
    sort_order: int = 0

    model_config = {"from_attributes": True}


class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    sort_order: int = 0


class CategoryUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = None
    sort_order: int | None = None


class NoteCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(default="")
    summary: str | None = None
    category_id: uuid.UUID | None = None
    tag_names: list[str] = Field(default_factory=list)
    is_favorite: bool = False
    mastery_level: int = Field(default=0, ge=0, le=2)
    source_type: str = Field(default="manual", max_length=20)
    source_url: str | None = None


class NoteUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=200)
    content: str | None = None
    summary: str | None = None
    category_id: uuid.UUID | None = None
    tag_names: list[str] | None = None
    is_favorite: bool | None = None
    mastery_level: int | None = Field(None, ge=0, le=2)
    source_type: str | None = Field(None, max_length=20)
    source_url: str | None = None


class NoteOut(BaseModel):
    id: uuid.UUID
    title: str
    content: str
    summary: str | None = None
    category: CategoryOut | None = None
    tags: list[TagOut] = []
    is_favorite: bool = False
    mastery_level: int = 0
    source_type: str = "manual"
    source_url: str | None = None
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
    mastery_level: int = 0
    source_type: str = "manual"
    source_url: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
