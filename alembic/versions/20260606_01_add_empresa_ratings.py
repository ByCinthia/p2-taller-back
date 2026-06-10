"""Add company reputation fields

Revision ID: 20260606_01_add_empresa_ratings
Revises: 20260429_01_current_models
Create Date: 2026-06-06
"""

from alembic import op
import sqlalchemy as sa

revision = "20260606_01_add_empresa_ratings"
down_revision = "20260505_01_add_user_fcm_token"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "empresa",
        sa.Column("estrellas_promedio", sa.Numeric(3, 2), nullable=False, server_default="5.00"),
    )
    op.add_column(
        "empresa",
        sa.Column("total_calificaciones", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("empresa", "total_calificaciones")
    op.drop_column("empresa", "estrellas_promedio")
