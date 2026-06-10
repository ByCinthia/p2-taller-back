"""Current models schema

Revision ID: 20260429_01_current_models
Revises:
Create Date: 2026-04-29
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260429_01_current_models"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "auth_user",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("password", sa.String(length=128), nullable=False),
        sa.Column("last_login", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_superuser", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("username", sa.String(length=150), nullable=False),
        sa.Column("first_name", sa.String(length=150), nullable=False, server_default=""),
        sa.Column("last_name", sa.String(length=150), nullable=False, server_default=""),
        sa.Column("email", sa.String(length=254), nullable=False, server_default=""),
        sa.Column("is_staff", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("date_joined", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
    )

    op.create_table(
        "empresa",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("nombre", sa.String(length=100), nullable=False),
        sa.Column("nit", sa.String(length=20), nullable=False),
        sa.Column("direccion", sa.String(length=255), nullable=True),
        sa.Column("telefono", sa.String(length=20), nullable=True),
        sa.Column("email", sa.String(length=100), nullable=True),
        sa.Column("latitud", sa.Numeric(precision=9, scale=6), nullable=True),
        sa.Column("longitud", sa.Numeric(precision=9, scale=6), nullable=True),
        sa.Column("fecha_creacion", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("nombre"),
        sa.UniqueConstraint("nit"),
    )

    op.create_table(
        "permisos",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("nombre", sa.String(length=100), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("nombre"),
    )

    op.create_table(
        "cargo",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("empresa_id", sa.String(length=36), nullable=False),
        sa.Column("nombre", sa.String(length=100), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresa.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "roles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("empresa_id", sa.String(length=36), nullable=False),
        sa.Column("nombre", sa.String(length=100), nullable=False),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresa.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "servicio",
        sa.Column("id_servicio", sa.String(length=36), nullable=False),
        sa.Column("empresa_id", sa.String(length=36), nullable=False),
        sa.Column("nombre", sa.String(length=100), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresa.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id_servicio"),
    )

    op.create_table(
        "empleado",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("empresa_id", sa.String(length=36), nullable=False),
        sa.Column("ci", sa.String(length=20), nullable=False),
        sa.Column("nombre_completo", sa.String(length=201), nullable=False),
        sa.Column("direccion", sa.String(length=255), nullable=True),
        sa.Column("telefono", sa.String(length=20), nullable=True),
        sa.Column("sueldo", sa.Numeric(precision=10, scale=2), nullable=False, server_default="0"),
        sa.Column("cargo_id", sa.String(length=36), nullable=True),
        sa.Column("foto_perfil", sa.String(length=100), nullable=True),
        sa.Column("fcm_token", sa.String(length=255), nullable=True),
        sa.Column("latitud_actual", sa.Numeric(precision=9, scale=6), nullable=True),
        sa.Column("longitud_actual", sa.Numeric(precision=9, scale=6), nullable=True),
        sa.Column("ubicacion_actualizada_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("disponible", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(["cargo_id"], ["cargo.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresa.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["usuario_id"], ["auth_user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("usuario_id"),
    )

    op.create_table(
        "suscripcion",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("empresa_id", sa.String(length=36), nullable=False),
        sa.Column("plan", sa.String(length=20), nullable=False, server_default="basico"),
        sa.Column("estado", sa.String(length=20), nullable=False, server_default="activa"),
        sa.Column("fecha_inicio", sa.Date(), nullable=False),
        sa.Column("fecha_fin", sa.Date(), nullable=False),
        sa.Column("max_usuarios", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("max_activos", sa.Integer(), nullable=False, server_default="50"),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresa.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("empresa_id"),
    )

    op.create_table(
        "roles_permisos",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("roles_id", sa.String(length=36), nullable=False),
        sa.Column("permisos_id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["permisos_id"], ["permisos.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["roles_id"], ["roles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "empleado_roles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("empleado_id", sa.String(length=36), nullable=False),
        sa.Column("roles_id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["empleado_id"], ["empleado.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["roles_id"], ["roles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "cliente",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=True),
        sa.Column("nombre", sa.String(length=150), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=True),
        sa.Column("telefono", sa.String(length=20), nullable=True),
        sa.Column("fcm_token", sa.String(length=255), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(["usuario_id"], ["auth_user.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("usuario_id"),
    )

    op.create_table(
        "vehiculo",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("cliente_id", sa.String(length=36), nullable=False),
        sa.Column("ano", sa.Integer(), nullable=True),
        sa.Column("placa", sa.String(length=20), nullable=True),
        sa.Column("marca", sa.String(length=50), nullable=True),
        sa.Column("modelo", sa.String(length=50), nullable=True),
        sa.Column("principal", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.ForeignKeyConstraint(["cliente_id"], ["cliente.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "incidente",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("cliente_id", sa.String(length=36), nullable=True),
        sa.Column("vehiculo_id", sa.String(length=36), nullable=True),
        sa.Column("tipo", sa.String(length=100), nullable=True),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("estado", sa.String(length=50), nullable=False, server_default="pendiente"),
        sa.Column("prioridad", sa.Integer(), nullable=True),
        sa.Column("latitud", sa.Numeric(precision=9, scale=6), nullable=True),
        sa.Column("longitud", sa.Numeric(precision=9, scale=6), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["cliente_id"], ["cliente.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["vehiculo_id"], ["vehiculo.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "asignacion_servicio",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("incidente_id", sa.String(length=36), nullable=False),
        sa.Column("empleado_id", sa.String(length=36), nullable=False),
        sa.Column("servicio_id", sa.String(length=36), nullable=False),
        sa.Column("empresa_id", sa.String(length=36), nullable=False),
        sa.Column("estado_tarea", sa.String(length=50), nullable=False, server_default="asignada"),
        sa.Column("tiempo_estimado_llegada_minutos", sa.Integer(), nullable=True),
        sa.Column("costo_servicio", sa.Numeric(12, 2), nullable=True),
        sa.Column("porcentaje_comision", sa.Numeric(5, 2), nullable=True),
        sa.Column("monto_comision", sa.Numeric(12, 2), nullable=True),
        sa.Column("fecha_asignacion", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fecha_cierre", sa.DateTime(timezone=True), nullable=True),
        sa.Column("motivo_cancelacion", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresa.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["empleado_id"], ["empleado.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["incidente_id"], ["incidente.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["servicio_id"], ["servicio.id_servicio"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "pago",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("asignacion_id", sa.String(length=36), nullable=False),
        sa.Column("incidente_id", sa.String(length=36), nullable=True),
        sa.Column("cliente_id", sa.String(length=36), nullable=True),
        sa.Column("empresa_id", sa.String(length=36), nullable=True),
        sa.Column("monto_total", sa.Numeric(12, 2), nullable=False),
        sa.Column("metodo_pago", sa.String(length=30), nullable=False),
        sa.Column("estado", sa.String(length=30), nullable=False, server_default="pendiente"),
        sa.Column("comision_plataforma", sa.Numeric(12, 2), nullable=True),
        sa.Column("monto_taller", sa.Numeric(12, 2), nullable=True),
        sa.Column("fecha_creacion", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fecha_confirmacion", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["asignacion_id"], ["asignacion_servicio.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["cliente_id"], ["cliente.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresa.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["incidente_id"], ["incidente.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "evidencia",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("incidente_id", sa.String(length=36), nullable=False),
        sa.Column("tipo", sa.String(length=50), nullable=False),
        sa.Column("url_archivo", sa.String(length=255), nullable=True),
        sa.Column("texto", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["incidente_id"], ["incidente.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "diagnostico",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("incidente_id", sa.String(length=36), nullable=False),
        sa.Column("clasificacion", sa.Integer(), nullable=True),
        sa.Column("resumen", sa.Text(), nullable=True),
        sa.Column("prioridad", sa.Integer(), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["incidente_id"], ["incidente.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("diagnostico")
    op.drop_table("evidencia")
    op.drop_table("pago")
    op.drop_table("asignacion_servicio")
    op.drop_table("incidente")
    op.drop_table("vehiculo")
    op.drop_table("cliente")
    op.drop_table("empleado_roles")
    op.drop_table("roles_permisos")
    op.drop_table("suscripcion")
    op.drop_table("empleado")
    op.drop_table("servicio")
    op.drop_table("roles")
    op.drop_table("cargo")
    op.drop_table("permisos")
    op.drop_table("empresa")
    op.drop_table("auth_user")