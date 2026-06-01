"""add users notes review tables

Revision ID: 9a3c2f1d4b7e
Revises: 58ffbfa37a16
Create Date: 2026-06-01 16:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision: str = "9a3c2f1d4b7e"
down_revision: Union[str, Sequence[str], None] = "58ffbfa37a16"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


LEGACY_USER_ID = "00000000-0000-0000-0000-000000000001"


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("username", sa.String(50), nullable=False),
        sa.Column("email", sa.String(100), nullable=True),
        sa.Column("password_hash", sa.String(200), nullable=False),
        sa.Column("reminder_enabled", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("reminder_time", sa.Time(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint("username"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_username", "users", ["username"])

    op.execute(
        f"""
        INSERT INTO users (id, username, email, password_hash, reminder_enabled)
        VALUES ('{LEGACY_USER_ID}'::uuid, 'legacy', NULL, 'legacy-disabled', false)
        ON CONFLICT (username) DO NOTHING
        """
    )

    op.add_column("notes", sa.Column("user_id", UUID(as_uuid=True), nullable=True))
    op.add_column("notes", sa.Column("mastery_level", sa.Integer(), server_default="0", nullable=False))
    op.add_column("notes", sa.Column("source_type", sa.String(20), server_default="manual", nullable=False))
    op.add_column("notes", sa.Column("source_url", sa.Text(), nullable=True))

    op.execute(f"UPDATE notes SET user_id = '{LEGACY_USER_ID}'::uuid WHERE user_id IS NULL")
    op.alter_column("notes", "user_id", nullable=False)
    op.create_foreign_key("fk_notes_user_id_users", "notes", "users", ["user_id"], ["id"], ondelete="CASCADE")

    op.create_table(
        "review_cards",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("note_id", UUID(as_uuid=True), sa.ForeignKey("notes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("card_type", sa.String(20), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("next_review_at", sa.DateTime(), nullable=True),
        sa.Column("ease_factor", sa.Float(), server_default="2.5", nullable=False),
        sa.Column("interval_days", sa.Integer(), server_default="0", nullable=False),
        sa.Column("review_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("is_user_edited", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("is_flagged", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_review_cards_note_id", "review_cards", ["note_id"])
    op.create_index("ix_review_cards_next_review_at", "review_cards", ["next_review_at"])

    op.create_table(
        "review_records",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("card_id", UUID(as_uuid=True), sa.ForeignKey("review_cards.id", ondelete="CASCADE"), nullable=False),
        sa.Column("quality", sa.Integer(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_review_records_card_id", "review_records", ["card_id"])


def downgrade() -> None:
    op.drop_index("ix_review_records_card_id", table_name="review_records")
    op.drop_table("review_records")
    op.drop_index("ix_review_cards_next_review_at", table_name="review_cards")
    op.drop_index("ix_review_cards_note_id", table_name="review_cards")
    op.drop_table("review_cards")

    op.drop_constraint("fk_notes_user_id_users", "notes", type_="foreignkey")
    op.drop_column("notes", "source_url")
    op.drop_column("notes", "source_type")
    op.drop_column("notes", "mastery_level")
    op.drop_column("notes", "user_id")

    op.drop_index("ix_users_username", table_name="users")
    op.drop_table("users")
