"""Add fcm_token column to cliente and empleado tables

Revision ID: 20260429_01_add_fcm
Revises: 20260429_01_current_models
Create Date: 2026-04-29
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260429_01_add_fcm"
down_revision: Union[str, None] = "20260429_01_current_models"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table"""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col['name'] for col in inspector.get_columns(table_name)}
    return column_name in columns


def upgrade() -> None:
    """Add fcm_token column to cliente and empleado tables"""
    # Add fcm_token to cliente table
    if not _column_exists('cliente', 'fcm_token'):
        op.add_column(
            'cliente',
            sa.Column('fcm_token', sa.String(length=255), nullable=True)
        )
        print("[Alembic] Column 'fcm_token' added to table 'cliente'")
    else:
        print("[Alembic] Column 'fcm_token' already exists in table 'cliente'")
    
    # Add fcm_token to empleado table
    if not _column_exists('empleado', 'fcm_token'):
        op.add_column(
            'empleado',
            sa.Column('fcm_token', sa.String(length=255), nullable=True)
        )
        print("[Alembic] Column 'fcm_token' added to table 'empleado'")
    else:
        print("[Alembic] Column 'fcm_token' already exists in table 'empleado'")


def downgrade() -> None:
    """Remove fcm_token column from cliente and empleado tables"""
    # Remove fcm_token from empleado
    if _column_exists('empleado', 'fcm_token'):
        op.drop_column('empleado', 'fcm_token')
        print("[Alembic] Column 'fcm_token' removed from table 'empleado'")
    
    # Remove fcm_token from cliente
    if _column_exists('cliente', 'fcm_token'):
        op.drop_column('cliente', 'fcm_token')
        print("[Alembic] Column 'fcm_token' removed from table 'cliente'")
