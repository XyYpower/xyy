"""add llm_model to users

Revision ID: df925bb28bcf
Revises: 86386e2a8c02
Create Date: 2026-06-15 13:52:18.779528

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'df925bb28bcf'
down_revision: Union[str, Sequence[str], None] = '86386e2a8c02'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('llm_model', sa.String(length=80), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'llm_model')
