"""ocr jobs

Revision ID: a1c9f7b2e4d0
Revises: 0149a6961387
Create Date: 2026-09-07 00:00:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1c9f7b2e4d0'
down_revision: Union[str, None] = '0149a6961387'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'ocr_jobs',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('api_client_id', sa.Uuid(), nullable=True),
        sa.Column('created_by_user_id', sa.Uuid(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('original_filename', sa.String(length=512), nullable=True),
        sa.Column('content_type', sa.String(length=128), nullable=True),
        sa.Column('size_bytes', sa.Integer(), nullable=False),
        sa.Column('storage_path', sa.String(length=1024), nullable=False),
        sa.Column('lang', sa.String(length=16), nullable=False),
        sa.Column('page_count', sa.Integer(), nullable=True),
        sa.Column('result', sa.JSON(), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('callback_url', sa.String(length=1024), nullable=True),
        sa.Column('callback_status', sa.String(length=64), nullable=True),
        sa.Column('attempts', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['api_client_id'], ['api_clients.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_ocr_jobs_api_client_id'), 'ocr_jobs', ['api_client_id'], unique=False)
    op.create_index(op.f('ix_ocr_jobs_created_by_user_id'), 'ocr_jobs', ['created_by_user_id'], unique=False)
    op.create_index(op.f('ix_ocr_jobs_status'), 'ocr_jobs', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_ocr_jobs_status'), table_name='ocr_jobs')
    op.drop_index(op.f('ix_ocr_jobs_created_by_user_id'), table_name='ocr_jobs')
    op.drop_index(op.f('ix_ocr_jobs_api_client_id'), table_name='ocr_jobs')
    op.drop_table('ocr_jobs')
