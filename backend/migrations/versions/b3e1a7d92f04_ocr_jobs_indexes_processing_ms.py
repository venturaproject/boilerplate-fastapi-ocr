"""ocr_jobs: composite indexes + processing_ms

Revision ID: b3e1a7d92f04
Revises: a1c9f7b2e4d0
Create Date: 2026-09-07 00:00:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b3e1a7d92f04'
down_revision: Union[str, None] = 'a1c9f7b2e4d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('ocr_jobs', sa.Column('processing_ms', sa.Integer(), nullable=True))
    op.drop_index(op.f('ix_ocr_jobs_status'), table_name='ocr_jobs')
    op.create_index('ix_ocr_jobs_status_created', 'ocr_jobs', ['status', 'created_at'], unique=False)
    op.create_index('ix_ocr_jobs_status_started', 'ocr_jobs', ['status', 'started_at'], unique=False)
    op.create_index('ix_ocr_jobs_client_created', 'ocr_jobs', ['api_client_id', 'created_at'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_ocr_jobs_client_created', table_name='ocr_jobs')
    op.drop_index('ix_ocr_jobs_status_started', table_name='ocr_jobs')
    op.drop_index('ix_ocr_jobs_status_created', table_name='ocr_jobs')
    op.create_index(op.f('ix_ocr_jobs_status'), 'ocr_jobs', ['status'], unique=False)
    op.drop_column('ocr_jobs', 'processing_ms')
