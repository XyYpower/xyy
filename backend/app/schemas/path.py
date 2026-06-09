import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class PathGenerateRequest(BaseModel):
    goal: str = Field(..., min_length=2, max_length=200)


class LearningPathModuleOut(BaseModel):
    name: str = Field(..., min_length=1)
    topics: list[str] = Field(..., min_length=1)
    priority: int = Field(..., ge=0)


class LearningPathOut(BaseModel):
    id: uuid.UUID
    name: str
    description: str
    modules: list[LearningPathModuleOut] = []
    created_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def model_validate(cls, obj, **kwargs):
        if isinstance(obj, dict):
            return super().model_validate(obj, **kwargs)
        # 兼容旧字段名 modules 和新的 modules_json
        modules_data = getattr(obj, "modules_json", None) or getattr(obj, "modules", None) or []
        obj_dict = {
            "id": obj.id,
            "name": obj.name,
            "description": obj.description,
            "created_at": obj.created_at,
            "modules": modules_data,
        }
        return cls(**obj_dict)
