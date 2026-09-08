"""documents.extraction

Revision ID: f1a2b3c4d5e6
Revises: e7b04c1f8a92
Create Date: 2026-09-07 00:00:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, None] = 'e7b04c1f8a92'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('documents', sa.Column('extraction', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('documents', 'extraction')
