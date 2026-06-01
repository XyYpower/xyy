import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ReviewCard(Base):
    """复习卡片表，SM-2 调度状态存储在卡片维度。"""

    __tablename__ = "review_cards"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    note_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("notes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    card_type: Mapped[str] = mapped_column(String(20), nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    next_review_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    ease_factor: Mapped[float] = mapped_column(Float, default=2.5, server_default="2.5")
    interval_days: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    review_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    last_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_user_edited: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    is_flagged: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    note: Mapped["Note"] = relationship("Note", back_populates="review_cards")  # noqa: F821
    records: Mapped[list["ReviewRecord"]] = relationship(
        "ReviewRecord", back_populates="card", cascade="all, delete-orphan"
    )


class ReviewRecord(Base):
    """复习历史表。"""

    __tablename__ = "review_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    card_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("review_cards.id", ondelete="CASCADE"), nullable=False, index=True
    )
    quality: Mapped[int] = mapped_column(Integer, nullable=False)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    card: Mapped[ReviewCard] = relationship("ReviewCard", back_populates="records")

