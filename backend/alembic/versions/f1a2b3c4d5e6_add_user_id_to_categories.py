"""add user id to categories

Revision ID: f1a2b3c4d5e6
Revises: e2b1a0d9c6f4
Create Date: 2026-06-02 14:30:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, None] = "e2b1a0d9c6f4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("categories", sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True))

    # 先按现有笔记的所属用户回填分类归属，尽量保留真实数据关系。
    op.execute(
        """
        UPDATE categories AS c
        SET user_id = owner.user_id
        FROM (
            SELECT DISTINCT ON (category_id) category_id, user_id
            FROM notes
            WHERE category_id IS NOT NULL
            ORDER BY category_id, created_at
        ) AS owner
        WHERE c.id = owner.category_id
          AND c.user_id IS NULL
        """
    )
    op.execute(
        """
        UPDATE categories
        SET user_id = (SELECT id FROM users ORDER BY created_at LIMIT 1)
        WHERE user_id IS NULL
          AND EXISTS (SELECT 1 FROM users)
        """
    )
    op.execute("DELETE FROM categories WHERE user_id IS NULL")

    op.alter_column("categories", "user_id", nullable=False)
    op.create_foreign_key(
        "fk_categories_user_id_users",
        "categories",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(op.f("ix_categories_user_id"), "categories", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_categories_user_id"), table_name="categories")
    op.drop_constraint("fk_categories_user_id_users", "categories", type_="foreignkey")
    op.drop_column("categories", "user_id")
