import uuid
from datetime import datetime, time

from pydantic import BaseModel, Field, field_validator, model_validator


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=128)
    email: str | None = Field(None, max_length=100)


class LoginRequest(BaseModel):
    username: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class UpdateProfileRequest(BaseModel):
    email: str | None = Field(None, max_length=100)
    reminder_enabled: bool | None = None
    reminder_time: str | None = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if not v:
            return None
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("邮箱格式不正确")
        return v


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., min_length=6)
    new_password: str = Field(..., min_length=6, max_length=128)


class UserOut(BaseModel):
    id: uuid.UUID
    username: str
    email: str | None = None
    reminder_enabled: bool = False
    reminder_time: time | None = None
    llm_provider: str | None = None
    llm_model: str | None = None
    llm_api_key_set: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def compute_api_key_set(cls, data):
        if hasattr(data, "llm_api_key"):
            values = {}
            for k in cls.model_fields:
                if k == "llm_api_key_set":
                    values[k] = bool(getattr(data, "llm_api_key", None))
                else:
                    values[k] = getattr(data, k, None)
            return values
        return data


class UpdateLLMSettingsRequest(BaseModel):
    llm_provider: str | None = Field(None, pattern="^(deepseek|openai|glm)$")
    llm_api_key: str | None = Field(None, max_length=200)
    llm_model: str | None = Field(None, max_length=80)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserOut
