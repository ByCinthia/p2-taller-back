from __future__ import annotations
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Table,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


roles_permisos = Table(
    "roles_permisos",
    Base.metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("roles_id", String(36), ForeignKey("roles.id", ondelete="CASCADE"), nullable=False),
    Column("permisos_id", String(36), ForeignKey("permisos.id", ondelete="CASCADE"), nullable=False),
)


empleado_roles = Table(
    "empleado_roles",
    Base.metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("empleado_id", String(36), ForeignKey("empleado.id", ondelete="CASCADE"), nullable=False),
    Column("roles_id", String(36), ForeignKey("roles.id", ondelete="CASCADE"), nullable=False),
)


class User(Base):
    __tablename__ = "auth_user"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    password: Mapped[str] = mapped_column(String(128), nullable=False)
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    username: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    first_name: Mapped[str] = mapped_column(String(150), default="")
    last_name: Mapped[str] = mapped_column(String(150), default="")
    email: Mapped[str] = mapped_column(String(254), default="")
    is_staff: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    date_joined: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fcm_token: Mapped[str | None] = mapped_column(String(255), nullable=True)

    empleado: Mapped[Empleado | None] = relationship(back_populates="usuario", uselist=False)
    notificaciones: Mapped[list[Notificacion]] = relationship(back_populates="usuario")


class Empresa(Base):
    __tablename__ = "empresa"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    nit: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    direccion: Mapped[str | None] = mapped_column(String(255), nullable=True)
    telefono: Mapped[str | None] = mapped_column(String(20), nullable=True)
    email: Mapped[str | None] = mapped_column(String(100), nullable=True)
    estrellas_promedio: Mapped[Decimal] = mapped_column(Numeric(3, 2), nullable=False, default=Decimal("5.00"))
    total_calificaciones: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    latitud: Mapped[Numeric | None] = mapped_column(Numeric(9, 6), nullable=True)
    longitud: Mapped[Numeric | None] = mapped_column(Numeric(9, 6), nullable=True)
    fecha_creacion: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    empleados: Mapped[list[Empleado]] = relationship(back_populates="empresa")
    servicios: Mapped[list[Servicio]] = relationship(back_populates="empresa")
    roles: Mapped[list[Rol]] = relationship(back_populates="empresa")
    suscripcion: Mapped[Suscripcion | None] = relationship(back_populates="empresa", uselist=False)


class Cargo(Base):
    __tablename__ = "cargo"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    empresa_id: Mapped[str] = mapped_column(String(36), ForeignKey("empresa.id", ondelete="CASCADE"), nullable=False)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)


class Servicio(Base):
    __tablename__ = "servicio"

    id_servicio: Mapped[str] = mapped_column(String(36), primary_key=True)
    empresa_id: Mapped[str] = mapped_column(String(36), ForeignKey("empresa.id", ondelete="CASCADE"), nullable=False)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)

    empresa: Mapped[Empresa] = relationship(back_populates="servicios")


class Permiso(Base):
    __tablename__ = "permisos"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)


class Rol(Base):
    __tablename__ = "roles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    empresa_id: Mapped[str] = mapped_column(String(36), ForeignKey("empresa.id", ondelete="CASCADE"), nullable=False)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)

    empresa: Mapped[Empresa] = relationship(back_populates="roles")
    permisos: Mapped[list[Permiso]] = relationship(secondary=roles_permisos)


class Empleado(Base):
    __tablename__ = "empleado"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    usuario_id: Mapped[int] = mapped_column(Integer, ForeignKey("auth_user.id", ondelete="CASCADE"), unique=True, nullable=False)
    empresa_id: Mapped[str] = mapped_column(String(36), ForeignKey("empresa.id", ondelete="CASCADE"), nullable=False)

    ci: Mapped[str] = mapped_column(String(20), nullable=False)
    nombre_completo: Mapped[str] = mapped_column(String(201), nullable=False)
    direccion: Mapped[str | None] = mapped_column(String(255), nullable=True)
    telefono: Mapped[str | None] = mapped_column(String(20), nullable=True)
    sueldo: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)

    cargo_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("cargo.id", ondelete="SET NULL"), nullable=True)

    foto_perfil: Mapped[str | None] = mapped_column(String(100), nullable=True)
    fcm_token: Mapped[str | None] = mapped_column(String(255), nullable=True)
    latitud_actual: Mapped[Numeric | None] = mapped_column(Numeric(9, 6), nullable=True)
    longitud_actual: Mapped[Numeric | None] = mapped_column(Numeric(9, 6), nullable=True)
    ubicacion_actualizada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    disponible: Mapped[bool] = mapped_column(Boolean, default=True)

    usuario: Mapped[User] = relationship(back_populates="empleado")
    empresa: Mapped[Empresa] = relationship(back_populates="empleados")
    cargo: Mapped[Cargo | None] = relationship()
    roles: Mapped[list[Rol]] = relationship(secondary=empleado_roles)


class Suscripcion(Base):
    __tablename__ = "suscripcion"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    empresa_id: Mapped[str] = mapped_column(String(36), ForeignKey("empresa.id", ondelete="CASCADE"), unique=True, nullable=False)
    plan: Mapped[str] = mapped_column(String(20), nullable=False, default="basico")
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="activa")
    fecha_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_fin: Mapped[date] = mapped_column(Date, nullable=False)
    max_usuarios: Mapped[int] = mapped_column(Integer, default=5)
    max_activos: Mapped[int] = mapped_column(Integer, default=50)

    empresa: Mapped[Empresa] = relationship(back_populates="suscripcion")


class Cliente(Base):
    __tablename__ = "cliente"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    usuario_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("auth_user.id", ondelete="SET NULL"), unique=True, nullable=True)
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str | None] = mapped_column(String(254), nullable=True)
    telefono: Mapped[str | None] = mapped_column(String(20), nullable=True)
    fcm_token: Mapped[str | None] = mapped_column(String(255), nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)

    usuario: Mapped[User | None] = relationship()
    vehiculos: Mapped[list["Vehiculo"]] = relationship(back_populates="cliente")

    @property
    def username(self) -> str | None:
        return self.usuario.username if self.usuario else None


class Notificacion(Base):
    __tablename__ = "notificacion"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("auth_user.id", ondelete="CASCADE"), nullable=False)
    titulo: Mapped[str] = mapped_column(String(150), nullable=False)
    mensaje: Mapped[str] = mapped_column(Text, nullable=False)
    tipo: Mapped[str | None] = mapped_column(String(50), nullable=True)
    data_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    leida: Mapped[bool] = mapped_column(Boolean, default=False)
    leida_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    creada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    usuario: Mapped[User] = relationship(back_populates="notificaciones")


class Vehiculo(Base):
    __tablename__ = "vehiculo"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    cliente_id: Mapped[str] = mapped_column(String(36), ForeignKey("cliente.id", ondelete="CASCADE"), nullable=False)
    ano: Mapped[int | None] = mapped_column("ano", Integer, nullable=True)
    placa: Mapped[str | None] = mapped_column(String(20), nullable=True)
    marca: Mapped[str | None] = mapped_column(String(50), nullable=True)
    modelo: Mapped[str | None] = mapped_column(String(50), nullable=True)
    principal: Mapped[bool] = mapped_column(Boolean, default=False)

  
    cliente: Mapped[Cliente] = relationship(back_populates="vehiculos")

    # keep backward-compatible attribute `anio` for Pydantic schemas and API
    @property
    def anio(self) -> int | None:
        return self.ano

    @anio.setter
    def anio(self, value: int | None) -> None:
        self.ano = value

class Incidente(Base):
    __tablename__ = "incidente"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    cliente_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("cliente.id", ondelete="SET NULL"),
        nullable=True,
    )

    vehiculo_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("vehiculo.id", ondelete="SET NULL"),
        nullable=True,
    )

    tipo: Mapped[str | None] = mapped_column(String(100), nullable=True)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    # lifecycle states: pendiente, aceptada, asignada, atendido, en_proceso, completada
    estado: Mapped[str] = mapped_column(
        SAEnum("pendiente", "aceptada", "asignada", "atendido", "en_proceso", "completada", name="incidente_estado"),
        nullable=False,
        default="pendiente",
    )
    accepted_empresa_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("empresa.id", ondelete="SET NULL"), nullable=True)
    prioridad: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latitud: Mapped[Numeric | None] = mapped_column(Numeric(9, 6), nullable=True)
    longitud: Mapped[Numeric | None] = mapped_column(Numeric(9, 6), nullable=True)

    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    cliente: Mapped[Cliente | None] = relationship()
    vehiculo: Mapped[Vehiculo | None] = relationship()
    evidencias: Mapped[list["Evidencia"]] = relationship(back_populates="incidente")
    diagnosticos: Mapped[list["Diagnostico"]] = relationship(back_populates="incidente")

class AsignacionServicio(Base):
    __tablename__ = "asignacion_servicio"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    incidente_id: Mapped[str] = mapped_column(String(36), ForeignKey("incidente.id", ondelete="CASCADE"), nullable=False)
    empleado_id: Mapped[str] = mapped_column(String(36), ForeignKey("empleado.id", ondelete="RESTRICT"), nullable=False)
    servicio_id: Mapped[str] = mapped_column(String(36), nullable=False)
    empresa_id: Mapped[str] = mapped_column(String(36), nullable=False)
    estado_tarea: Mapped[str] = mapped_column(String(50), nullable=False, default="asignada")
    tiempo_estimado_llegada_minutos: Mapped[int | None] = mapped_column(Integer, nullable=True)
    costo_servicio: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    porcentaje_comision: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    monto_comision: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    fecha_asignacion: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fecha_cierre: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    motivo_cancelacion: Mapped[str | None] = mapped_column(Text, nullable=True)

    incidente: Mapped[Incidente] = relationship()
    empleado: Mapped[Empleado] = relationship()


class Pago(Base):
    __tablename__ = "pago"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    asignacion_id: Mapped[str] = mapped_column(String(36), ForeignKey("asignacion_servicio.id", ondelete="CASCADE"), nullable=False)
    incidente_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("incidente.id", ondelete="SET NULL"), nullable=True)
    cliente_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("cliente.id", ondelete="SET NULL"), nullable=True)
    empresa_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("empresa.id", ondelete="SET NULL"), nullable=True)

    monto_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    metodo_pago: Mapped[str] = mapped_column(String(30), nullable=False)
    estado: Mapped[str] = mapped_column(String(30), nullable=False, default="pendiente")
    comision_plataforma: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    monto_taller: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)

    fecha_creacion: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fecha_confirmacion: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    asignacion: Mapped[AsignacionServicio] = relationship()
    incidente: Mapped[Incidente | None] = relationship()
    cliente: Mapped[Cliente | None] = relationship()
    empresa: Mapped[Empresa | None] = relationship()


class Evidencia(Base):
    __tablename__ = "evidencia"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    incidente_id: Mapped[str] = mapped_column(String(36), ForeignKey("incidente.id", ondelete="CASCADE"), nullable=False)
    tipo: Mapped[str] = mapped_column(String(50), nullable=False)  # foto, audio, otro
    url_archivo: Mapped[str | None] = mapped_column(String(255), nullable=True)
    texto: Mapped[str | None] = mapped_column(Text, nullable=True)

    incidente: Mapped[Incidente] = relationship(back_populates="evidencias")


class Diagnostico(Base):
    __tablename__ = "diagnostico"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    incidente_id: Mapped[str] = mapped_column(String(36), ForeignKey("incidente.id", ondelete="CASCADE"), nullable=False)
    clasificacion: Mapped[int | None] = mapped_column(Integer, nullable=True)
    resumen: Mapped[str | None] = mapped_column(Text, nullable=True)
    prioridad: Mapped[int | None] = mapped_column(Integer, nullable=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    incidente: Mapped[Incidente] = relationship(back_populates="diagnosticos")
