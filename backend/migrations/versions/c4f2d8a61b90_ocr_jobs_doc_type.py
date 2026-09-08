"""ocr_jobs: doc_type

Revision ID: c4f2d8a61b90
Revises: b3e1a7d92f04
Create Date: 2026-09-07 00:00:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c4f2d8a61b90'
down_revision: Union[str, None] = 'b3e1a7d92f04'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('ocr_jobs', sa.Column('doc_type', sa.String(length=40), nullable=True))


def downgrade() -> None:
    op.drop_column('ocr_jobs', 'doc_type')
