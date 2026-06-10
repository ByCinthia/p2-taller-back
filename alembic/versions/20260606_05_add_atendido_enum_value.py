"""Add 'atendido' value to incidente_estado enum

Revision ID: 20260606_05_add_atendido_enum_value
Revises: 20260606_04_add_incidente_estado
Create Date: 2026-06-06
"""

from alembic import op
import sqlalchemy as sa

revision = "20260606_05_add_atendido_enum_value"
down_revision = "20260606_04_add_incidente_estado"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add enum value 'atendido' if it does not exist
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_enum e
                JOIN pg_type t ON e.enumtypid = t.oid
                WHERE t.typname = 'incidente_estado' AND e.enumlabel = 'atendido'
            ) THEN
                ALTER TYPE incidente_estado ADD VALUE 'atendido';
            END IF;
        END$$;
        """
    )


def downgrade() -> None:
    # Removing enum labels is non-trivial and PostgreSQL doesn't support
    # dropping a single enum value. We'll leave it as no-op for downgrade.
    pass
