"""api_clients quotas + client_usage table

Revision ID: b8d4f02a6c17
Revises: a7c3e91b2f45
Create Date: 2026-09-07 00:00:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b8d4f02a6c17'
down_revision: Union[str, None] = 'a7c3e91b2f45'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('api_clients', sa.Column('rate_limit', sa.String(length=20), nullable=True))
    op.add_column('api_clients', sa.Column('monthly_page_quota', sa.Integer(), nullable=True))

    op.create_table(
        'client_usage',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('api_client_id', sa.Uuid(), nullable=False),
        sa.Column('period', sa.String(length=7), nullable=False),
        sa.Column('pages', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('requests', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['api_client_id'], ['api_clients.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('api_client_id', 'period', name='uq_client_usage_period'),
    )
    op.create_index(op.f('ix_client_usage_api_client_id'), 'client_usage', ['api_client_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_client_usage_api_client_id'), table_name='client_usage')
    op.drop_table('client_usage')
    op.drop_column('api_clients', 'monthly_page_quota')
    op.drop_column('api_clients', 'rate_limit')
