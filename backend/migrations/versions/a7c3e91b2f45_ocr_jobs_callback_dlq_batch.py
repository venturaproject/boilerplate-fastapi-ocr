"""ocr_jobs: callback dead-letter fields + batch_id

Revision ID: a7c3e91b2f45
Revises: f1a2b3c4d5e6
Create Date: 2026-09-07 00:00:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a7c3e91b2f45'
down_revision: Union[str, None] = 'f1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('ocr_jobs', sa.Column('callback_attempts', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('ocr_jobs', sa.Column('callback_last_error', sa.String(length=500), nullable=True))
    op.add_column('ocr_jobs', sa.Column('next_callback_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('ocr_jobs', sa.Column('batch_id', sa.Uuid(), nullable=True))
    op.create_index('ix_ocr_jobs_next_callback', 'ocr_jobs', ['next_callback_at'], unique=False)
    op.create_index('ix_ocr_jobs_batch', 'ocr_jobs', ['batch_id'], unique=False)
    op.alter_column('ocr_jobs', 'callback_attempts', server_default=None)


def downgrade() -> None:
    op.drop_index('ix_ocr_jobs_batch', table_name='ocr_jobs')
    op.drop_index('ix_ocr_jobs_next_callback', table_name='ocr_jobs')
    op.drop_column('ocr_jobs', 'batch_id')
    op.drop_column('ocr_jobs', 'next_callback_at')
    op.drop_column('ocr_jobs', 'callback_last_error')
    op.drop_column('ocr_jobs', 'callback_attempts')
