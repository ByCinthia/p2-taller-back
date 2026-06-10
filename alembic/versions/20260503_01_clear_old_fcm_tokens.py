"""Clear old FCM tokens from auxiliomecanico-f0789 project

Revision ID: 20260503_01_clear_old_fcm_tokens
Revises: 20260424_02_sync_cliente_usuario_id
Create Date: 2026-05-03 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260503_01_clear_old_fcm_tokens"
down_revision = "20260429_01_add_fcm"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Clear all FCM tokens to force re-registration with new Firebase project"""
    # Clear Empleado FCM tokens
    op.execute("UPDATE empleado SET fcm_token = NULL WHERE fcm_token IS NOT NULL")
    
    # Clear Cliente FCM tokens
    op.execute("UPDATE cliente SET fcm_token = NULL WHERE fcm_token IS NOT NULL")


def downgrade() -> None:
    """No downgrade needed - tokens are not recoverable anyway"""
    pass
