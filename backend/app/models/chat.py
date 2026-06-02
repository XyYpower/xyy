"""V2.3 预留的 Chat/RAG 数据模型。

当前 V2.1 不注册到 app.models.__init__，因此不会参与 Alembic 自动迁移。
等实现 RAG 对话时再补正式迁移和 pgvector 字段映射。
"""

import uuid
from datetime import datetime

from sqlalchemy import String, Text, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Conversation(Base):
    """对话表"""
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(200), nullable=False, default="新对话")
    note_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("notes.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # 关联
    messages: Mapped[list["Message"]] = relationship(
        "Message", back_populates="conversation", order_by="Message.created_at"
    )
    note: Mapped["Note | None"] = relationship("Note")  # noqa: F821


class Message(Base):
    """消息表"""
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # user / assistant / system
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sources: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # AI 引用的笔记列表
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # 关联
    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="messages")


class NoteEmbedding(Base):
    """笔记向量嵌入表（每条笔记一个嵌入）"""
    __tablename__ = "note_embeddings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    note_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("notes.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    # VECTOR(1536) 类型在迁移中通过 raw SQL 创建，此处用 Text 占位
    embedding: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)  # 被嵌入的文本
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # 关联
    note: Mapped["Note"] = relationship("Note")  # noqa: F821
