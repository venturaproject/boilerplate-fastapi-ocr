"""api_clients.ocr_extractor_override

Revision ID: d8f1c4a92b06
Revises: c9e1a4f7b230
Create Date: 2026-09-11 00:00:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd8f1c4a92b06'
down_revision: Union[str, None] = 'c9e1a4f7b230'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('api_clients', sa.Column('ocr_extractor_override', sa.String(length=10), nullable=True))


def downgrade() -> None:
    op.drop_column('api_clients', 'ocr_extractor_override')
