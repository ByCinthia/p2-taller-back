"""Add incidente estado enum and accepted_empresa_id

Revision ID: 20260606_04_add_incidente_estado
Revises: 20260606_01_add_empresa_ratings
Create Date: 2026-06-06
"""

from alembic import op
import sqlalchemy as sa

revision = "20260606_04_add_incidente_estado"
down_revision = "20260606_01_add_empresa_ratings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Use a PL/pgSQL block to perform idempotent changes and swallow non-fatal errors
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'incidente_estado') THEN
                CREATE TYPE incidente_estado AS ENUM ('pendiente','aceptada','asignada','en_proceso','completada');
            END IF;

            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='incidente' AND column_name='estado') THEN
                ALTER TABLE incidente ADD COLUMN estado incidente_estado DEFAULT 'pendiente' NOT NULL;
            ELSE
                BEGIN
                    ALTER TABLE incidente ALTER COLUMN estado TYPE incidente_estado USING estado::incidente_estado;
                EXCEPTION WHEN others THEN
                    -- ignore conversion errors
                    NULL;
                END;
            END IF;

            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='incidente' AND column_name='accepted_empresa_id') THEN
                ALTER TABLE incidente ADD COLUMN accepted_empresa_id VARCHAR(36);
                BEGIN
                    ALTER TABLE incidente ADD CONSTRAINT fk_incidente_accepted_empresa FOREIGN KEY (accepted_empresa_id) REFERENCES empresa(id) ON DELETE SET NULL;
                EXCEPTION WHEN others THEN
                    NULL;
                END;
            END IF;
        END$$;
        """
    )


def downgrade() -> None:
    op.drop_constraint('fk_incidente_accepted_empresa', 'incidente', type_='foreignkey')
    op.drop_column('incidente', 'accepted_empresa_id')
    # revert estado column to text then drop enum type
    op.execute("ALTER TABLE incidente ALTER COLUMN estado TYPE VARCHAR")
    op.drop_column('incidente', 'estado')
    op.execute('DROP TYPE IF EXISTS incidente_estado')
