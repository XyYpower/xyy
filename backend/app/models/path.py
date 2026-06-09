import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class LearningPath(Base):
    """学习路径表，modules 用 JSONB 存储 MVP 结构。"""

    __tablename__ = "learning_paths"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    modules_json: Mapped[list[dict]] = mapped_column("modules", JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User"] = relationship("User")  # noqa: F821
    structured_modules: Mapped[list["LearningPathModule"]] = relationship(
        "LearningPathModule", back_populates="path", cascade="all, delete-orphan",
        order_by="LearningPathModule.order_index",
    )


class LearningPathModule(Base):
    """学习路径模块表：将 JSONB modules 拆为结构化记录。"""

    __tablename__ = "learning_path_modules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    path_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("learning_paths.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="not_started")

    path: Mapped["LearningPath"] = relationship("LearningPath", back_populates="structured_modules")  # noqa: F821
    topics: Mapped[list["LearningPathTopic"]] = relationship(
        "LearningPathTopic", back_populates="module", cascade="all, delete-orphan",
        order_by="LearningPathTopic.priority",
    )


class LearningPathTopic(Base):
    """学习路径 Topic 表：模块内的具体知识点目标。"""

    __tablename__ = "learning_path_topics"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    module_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("learning_path_modules.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    objective: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="not_started")
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    linked_note_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("notes.id", ondelete="SET NULL"), nullable=True
    )
    mastery_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    module: Mapped["LearningPathModule"] = relationship("LearningPathModule", back_populates="topics")  # noqa: F821
    linked_note: Mapped["Note | None"] = relationship("Note")  # noqa: F821
    tasks: Mapped[list["LearningTask"]] = relationship(
        "LearningTask", back_populates="topic", cascade="all, delete-orphan"
    )


class LearningTask(Base):
    """学习任务表：每天可执行的具体任务。"""

    __tablename__ = "learning_tasks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    topic_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("learning_path_topics.id", ondelete="SET NULL"), nullable=True
    )
    task_type: Mapped[str] = mapped_column(String(30), nullable=False, default="learn")
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    due_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    agent_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    topic: Mapped["LearningPathTopic | None"] = relationship("LearningPathTopic", back_populates="tasks")  # noqa: F821
    user: Mapped["User"] = relationship("User")  # noqa: F821
