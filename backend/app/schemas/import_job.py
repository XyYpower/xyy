import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ImportTextRequest(BaseModel):
    text: str = Field(..., min_length=10)
    source_url: str | None = None


class ImportUrlRequest(BaseModel):
    url: str = Field(..., max_length=2000)


class ImportCodeRequest(BaseModel):
    code: str = Field(..., min_length=5)
    language: str | None = None


class DraftUpdateRequest(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=200)
    content: str | None = None
    is_selected: bool | None = None


class ImportJobOut(BaseModel):
    id: uuid.UUID
    source_type: str
    source_url: str | None = None
    status: str
    error_message: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ExtractionDraftOut(BaseModel):
    id: uuid.UUID
    title: str
    content: str
    is_selected: bool
    note_id: uuid.UUID | None = None

    model_config = {"from_attributes": True}


class ImportResultOut(BaseModel):
    job: ImportJobOut
    drafts: list[ExtractionDraftOut]
