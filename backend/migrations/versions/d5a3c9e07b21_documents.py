"""documents registry

Revision ID: d5a3c9e07b21
Revises: c4f2d8a61b90
Create Date: 2026-09-07 00:00:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd5a3c9e07b21'
down_revision: Union[str, None] = 'c4f2d8a61b90'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'documents',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('api_client_id', sa.Uuid(), nullable=True),
        sa.Column('created_by_user_id', sa.Uuid(), nullable=True),
        sa.Column('ocr_job_id', sa.Uuid(), nullable=True),
        sa.Column('mode', sa.String(length=16), nullable=False),
        sa.Column('status', sa.String(length=16), nullable=False),
        sa.Column('original_filename', sa.String(length=512), nullable=True),
        sa.Column('content_type', sa.String(length=128), nullable=True),
        sa.Column('size_bytes', sa.Integer(), nullable=False),
        sa.Column('lang', sa.String(length=16), nullable=False),
        sa.Column('page_count', sa.Integer(), nullable=True),
        sa.Column('processing_ms', sa.Integer(), nullable=True),
        sa.Column('doc_type', sa.String(length=40), nullable=True),
        sa.Column('doc_type_confidence', sa.Float(), nullable=True),
        sa.Column('char_count', sa.Integer(), nullable=True),
        sa.Column('text_excerpt', sa.Text(), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['api_client_id'], ['api_clients.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['ocr_job_id'], ['ocr_jobs.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('ocr_job_id'),
    )
    op.create_index(op.f('ix_documents_api_client_id'), 'documents', ['api_client_id'], unique=False)
    op.create_index(op.f('ix_documents_created_by_user_id'), 'documents', ['created_by_user_id'], unique=False)
    op.create_index('ix_documents_client_created', 'documents', ['api_client_id', 'created_at'], unique=False)
    op.create_index('ix_documents_mode_created', 'documents', ['mode', 'created_at'], unique=False)
    op.create_index('ix_documents_doc_type', 'documents', ['doc_type'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_documents_doc_type', table_name='documents')
    op.drop_index('ix_documents_mode_created', table_name='documents')
    op.drop_index('ix_documents_client_created', table_name='documents')
    op.drop_index(op.f('ix_documents_created_by_user_id'), table_name='documents')
    op.drop_index(op.f('ix_documents_api_client_id'), table_name='documents')
    op.drop_table('documents')
