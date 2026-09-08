"""audit_events table + user login-lockout columns

Revision ID: c9e1a4f7b230
Revises: b8d4f02a6c17
Create Date: 2026-09-08 00:00:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c9e1a4f7b230'
down_revision: Union[str, None] = 'b8d4f02a6c17'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column('failed_login_attempts', sa.Integer(), nullable=False, server_default='0'),
    )
    op.add_column('users', sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        'audit_events',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('action', sa.String(length=64), nullable=False),
        sa.Column('actor_type', sa.String(length=16), nullable=False),
        sa.Column('actor_id', sa.Uuid(), nullable=True),
        sa.Column('actor_label', sa.String(length=255), nullable=True),
        sa.Column('target', sa.String(length=255), nullable=True),
        sa.Column('ip', sa.String(length=64), nullable=True),
        sa.Column('meta', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_audit_events_created_at'), 'audit_events', ['created_at'], unique=False)
    op.create_index(op.f('ix_audit_events_action'), 'audit_events', ['action'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_audit_events_action'), table_name='audit_events')
    op.drop_index(op.f('ix_audit_events_created_at'), table_name='audit_events')
    op.drop_table('audit_events')
    op.drop_column('users', 'locked_until')
    op.drop_column('users', 'failed_login_attempts')
