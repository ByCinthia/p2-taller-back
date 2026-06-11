"""Add fcm_token to auth_user

Revision ID: 20260505_01_add_user_fcm_token
Revises: 20260504_01_notificaciones
Create Date: 2026-05-05
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260505_01_add_user_fcm_token"
down_revision: Union[str, None] = "20260504_01_notificaciones"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns(table_name)}
    return column_name in columns


def upgrade() -> None:
    if not _column_exists("auth_user", "fcm_token"):
        op.add_column("auth_user", sa.Column("fcm_token", sa.String(length=255), nullable=True))


def downgrade() -> None:
    if _column_exists("auth_user", "fcm_token"):
        op.drop_column("auth_user", "fcm_token")
