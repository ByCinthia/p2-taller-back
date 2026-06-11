"""Create notificacion table

Revision ID: 20260504_01_notificaciones
Revises: 20260503_01_clear_old_fcm_tokens
Create Date: 2026-05-04
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260504_01_notificaciones"
down_revision: Union[str, None] = "20260503_01_clear_old_fcm_tokens"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "notificacion",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("titulo", sa.String(length=150), nullable=False),
        sa.Column("mensaje", sa.Text(), nullable=False),
        sa.Column("tipo", sa.String(length=50), nullable=True),
        sa.Column("data_json", sa.Text(), nullable=True),
        sa.Column("leida", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("leida_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("creada_en", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["auth_user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notificacion_user_id", "notificacion", ["user_id"])
    op.create_index("ix_notificacion_creada_en", "notificacion", ["creada_en"])


def downgrade() -> None:
    op.drop_index("ix_notificacion_creada_en", table_name="notificacion")
    op.drop_index("ix_notificacion_user_id", table_name="notificacion")
    op.drop_table("notificacion")
