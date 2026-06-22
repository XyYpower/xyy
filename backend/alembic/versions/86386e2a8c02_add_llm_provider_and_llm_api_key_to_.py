"""add llm_provider and llm_api_key to users

Revision ID: 86386e2a8c02
Revises: c3d4e5f6a7b8
Create Date: 2026-06-15 13:28:38.506640

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '86386e2a8c02'
down_revision: Union[str, Sequence[str], None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('llm_provider', sa.String(length=20), nullable=True))
    op.add_column('users', sa.Column('llm_api_key', sa.String(length=200), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'llm_api_key')
    op.drop_column('users', 'llm_provider')
