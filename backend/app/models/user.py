import uuid
from datetime import datetime, time

from sqlalchemy import Boolean, DateTime, String, Time, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    """用户表：用于认证和学习数据隔离。"""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    email: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)
    password_hash: Mapped[str] = mapped_column(String(200), nullable=False)
    reminder_enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    reminder_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    llm_provider: Mapped[str | None] = mapped_column(String(20), nullable=True)  # deepseek/openai/glm
    llm_api_key: Mapped[str | None] = mapped_column(String(200), nullable=True)
    llm_model: Mapped[str | None] = mapped_column(String(80), nullable=True)  # 用户选择的模型名
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    notes: Mapped[list["Note"]] = relationship("Note", back_populates="user")  # noqa: F821

