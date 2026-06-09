"""add structured learning path tables

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-06-03 14:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op


revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # learning_path_modules
    op.create_table(
        "learning_path_modules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("path_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("learning_paths.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, server_default=""),
        sa.Column("order_index", sa.Integer, server_default="0"),
        sa.Column("status", sa.String(20), server_default="not_started"),
    )
    op.create_index("ix_learning_path_modules_path_id", "learning_path_modules", ["path_id"])

    # learning_path_topics
    op.create_table(
        "learning_path_topics",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("module_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("learning_path_modules.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("objective", sa.Text, server_default=""),
        sa.Column("status", sa.String(20), server_default="not_started"),
        sa.Column("priority", sa.Integer, server_default="0"),
        sa.Column("linked_note_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("notes.id", ondelete="SET NULL"), nullable=True),
        sa.Column("mastery_score", sa.Float, server_default="0.0"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_learning_path_topics_module_id", "learning_path_topics", ["module_id"])

    # learning_tasks
    op.create_table(
        "learning_tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("topic_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("learning_path_topics.id", ondelete="SET NULL"), nullable=True),
        sa.Column("task_type", sa.String(30), server_default="learn"),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, server_default=""),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("due_at", sa.DateTime, nullable=True),
        sa.Column("completed_at", sa.DateTime, nullable=True),
        sa.Column("agent_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agent_runs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_learning_tasks_user_id", "learning_tasks", ["user_id"])
    op.create_index("ix_learning_tasks_topic_id", "learning_tasks", ["topic_id"])


def downgrade() -> None:
    op.drop_table("learning_tasks")
    op.drop_table("learning_path_topics")
    op.drop_table("learning_path_modules")
