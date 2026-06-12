"""Add 'cancelada' value to incidente_estado enum

Revision ID: 20260612_01_cancelada_enum
Revises: 20260606_05_atendido_enum
Create Date: 2026-06-12
"""

from alembic import op
import sqlalchemy as sa

revision = "20260612_01_cancelada_enum"
down_revision = "20260606_05_atendido_enum"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add enum value 'cancelada' if it does not exist
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_enum e
                JOIN pg_type t ON e.enumtypid = t.oid
                WHERE t.typname = 'incidente_estado' AND e.enumlabel = 'cancelada'
            ) THEN
                ALTER TYPE incidente_estado ADD VALUE 'cancelada';
            END IF;
        END$$;
        """
    )


def downgrade() -> None:
    # Removing enum labels is non-trivial in PostgreSQL (no DROP VALUE support).
    # This is a no-op for downgrade.
    pass
