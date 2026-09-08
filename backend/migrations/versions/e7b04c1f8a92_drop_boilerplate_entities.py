"""drop boilerplate demo entities (trabajador / telefono / dispositivo)

Revision ID: e7b04c1f8a92
Revises: d5a3c9e07b21
Create Date: 2026-09-07 00:00:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e7b04c1f8a92'
down_revision: Union[str, None] = 'd5a3c9e07b21'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Order matters: drop the tables holding the foreign keys first.
    op.drop_table('dispositivos')
    op.drop_table('telefonos')
    op.drop_table('device_models')
    op.drop_table('device_brands')
    op.drop_table('estado_telefonos')
    op.drop_table('tipologias')
    op.drop_table('trabajadores')


def downgrade() -> None:
    op.create_table(
        'device_brands',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('nombre', sa.String(length=100), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('nombre'),
    )
    op.create_table(
        'estado_telefonos',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('nombre', sa.String(length=100), nullable=False),
        sa.Column('color', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('nombre'),
    )
    op.create_table(
        'tipologias',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('nombre', sa.String(length=100), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('nombre'),
    )
    op.create_table(
        'trabajadores',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('nombre', sa.String(length=255), nullable=False),
        sa.Column('apellido', sa.String(length=255), nullable=False),
        sa.Column('synergy_res_id', sa.Integer(), nullable=True),
        sa.Column('dni', sa.String(length=20), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('telefono', sa.String(length=50), nullable=True),
        sa.Column('estado', sa.String(length=20), nullable=False),
        sa.Column('emp_stat', sa.String(length=50), nullable=True),
        sa.Column('cargo', sa.String(length=255), nullable=True),
        sa.Column('departamento', sa.String(length=255), nullable=True),
        sa.Column('loc', sa.String(length=100), nullable=True),
        sa.Column('ubicacion', sa.String(length=255), nullable=True),
        sa.Column('ciudad', sa.String(length=100), nullable=True),
        sa.Column('fecha_incorporacion', sa.Date(), nullable=True),
        sa.Column('fecha_baja', sa.Date(), nullable=True),
        sa.Column('observaciones', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('dni'),
        sa.UniqueConstraint('synergy_res_id'),
    )
    op.create_table(
        'device_models',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('nombre', sa.String(length=100), nullable=False),
        sa.Column('marca_id', sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(['marca_id'], ['device_brands.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'telefonos',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('numero', sa.String(length=50), nullable=True),
        sa.Column('tipo', sa.String(length=50), nullable=True),
        sa.Column('plan', sa.String(length=100), nullable=True),
        sa.Column('nplan', sa.String(length=100), nullable=True),
        sa.Column('pin', sa.String(length=20), nullable=True),
        sa.Column('puk', sa.String(length=20), nullable=True),
        sa.Column('imei', sa.String(length=100), nullable=True),
        sa.Column('imei2', sa.String(length=100), nullable=True),
        sa.Column('marca', sa.String(length=100), nullable=True),
        sa.Column('modelo', sa.String(length=100), nullable=True),
        sa.Column('linea', sa.String(length=100), nullable=True),
        sa.Column('operadora', sa.String(length=100), nullable=True),
        sa.Column('estado_id', sa.Uuid(), nullable=True),
        sa.Column('tipologia_id', sa.Uuid(), nullable=True),
        sa.Column('trabajador_id', sa.Uuid(), nullable=True),
        sa.Column('observaciones', sa.Text(), nullable=False),
        sa.Column('activo', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['estado_id'], ['estado_telefonos.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['tipologia_id'], ['tipologias.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['trabajador_id'], ['trabajadores.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'dispositivos',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('numero', sa.String(length=100), nullable=True),
        sa.Column('imei', sa.String(length=100), nullable=True),
        sa.Column('serie', sa.String(length=100), nullable=True),
        sa.Column('synergy_res_id', sa.Integer(), nullable=True),
        sa.Column('marca_id', sa.Uuid(), nullable=True),
        sa.Column('modelo_id', sa.Uuid(), nullable=True),
        sa.Column('grupo', sa.String(length=100), nullable=True),
        sa.Column('estado', sa.String(length=20), nullable=False),
        sa.Column('trabajador_id', sa.Uuid(), nullable=True),
        sa.Column('observaciones', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['marca_id'], ['device_brands.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['modelo_id'], ['device_models.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['trabajador_id'], ['trabajadores.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('imei'),
        sa.UniqueConstraint('synergy_res_id'),
    )
