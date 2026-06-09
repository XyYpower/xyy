"""add agent runtime tables

Revision ID: a1b2c3d4e5f6
Revises: f1a2b3c4d5e6
Create Date: 2026-06-03 10:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # agent_runs
    op.create_table(
        "agent_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("run_type", sa.String(40), nullable=False),
        sa.Column("goal", sa.Text, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="queued"),
        sa.Column("input", postgresql.JSONB, nullable=True),
        sa.Column("output", postgresql.JSONB, nullable=True),
        sa.Column("current_step", sa.String(100), nullable=True),
        sa.Column("total_prompt_tokens", sa.Integer, server_default="0"),
        sa.Column("total_completion_tokens", sa.Integer, server_default="0"),
        sa.Column("estimated_cost", sa.Float, server_default="0.0"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime, nullable=True),
    )
    op.create_index("ix_agent_runs_user_id", "agent_runs", ["user_id"])
    op.create_index("ix_agent_runs_run_type", "agent_runs", ["run_type"])
    op.create_index("ix_agent_runs_status", "agent_runs", ["status"])

    # agent_steps
    op.create_table(
        "agent_steps",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("step_order", sa.Integer, nullable=False),
        sa.Column("agent_name", sa.String(60), nullable=False),
        sa.Column("node_name", sa.String(80), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="running"),
        sa.Column("input", postgresql.JSONB, nullable=True),
        sa.Column("output", postgresql.JSONB, nullable=True),
        sa.Column("reasoning_summary", sa.Text, nullable=True),
        sa.Column("requires_approval", sa.Boolean, server_default="false"),
        sa.Column("approved_at", sa.DateTime, nullable=True),
        sa.Column("latency_ms", sa.Integer, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_agent_steps_run_id", "agent_steps", ["run_id"])

    # tool_calls
    op.create_table(
        "tool_calls",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("step_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agent_steps.id", ondelete="SET NULL"), nullable=True),
        sa.Column("tool_name", sa.String(80), nullable=False),
        sa.Column("arguments", postgresql.JSONB, nullable=True),
        sa.Column("result", postgresql.JSONB, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="success"),
        sa.Column("latency_ms", sa.Integer, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_tool_calls_run_id", "tool_calls", ["run_id"])

    # ai_call_logs
    op.create_table(
        "ai_call_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("agent_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agent_runs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("provider", sa.String(30), nullable=False),
        sa.Column("model", sa.String(80), nullable=False),
        sa.Column("purpose", sa.String(40), nullable=False),
        sa.Column("prompt_tokens", sa.Integer, server_default="0"),
        sa.Column("completion_tokens", sa.Integer, server_default="0"),
        sa.Column("estimated_cost", sa.Float, server_default="0.0"),
        sa.Column("latency_ms", sa.Integer, server_default="0"),
        sa.Column("status", sa.String(20), nullable=False, server_default="success"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_ai_call_logs_user_id", "ai_call_logs", ["user_id"])
    op.create_index("ix_ai_call_logs_purpose", "ai_call_logs", ["purpose"])


def downgrade() -> None:
    op.drop_table("ai_call_logs")
    op.drop_table("tool_calls")
    op.drop_table("agent_steps")
    op.drop_table("agent_runs")
