from decimal import Decimal

from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import ORMModel
from app.schemas.role import RoleOut


class MiAsignacionOut(BaseModel):
    incidente_id: str
    incidente_tipo: str | None = None
    incidente_descripcion: str | None = None
    incidente_estado: str | None = None
    incidente_latitud: float | None = None
    incidente_longitud: float | None = None
    prioridad: str | None = None
    cliente_nombre: str | None = None
    cliente_telefono: str | None = None
    vehiculo_marca: str | None = None
    vehiculo_modelo: str | None = None
    vehiculo_placa: str | None = None
    vehiculo_anio: int | None = None
    fecha_asignacion: str
    estado_tarea: str
    servicio_id: str | None = None
    servicio_nombre: str | None = None
    latitud_actual: float | None = None
    longitud_actual: float | None = None
    distancia_km: float | None = None
    eta_minutos: int | None = None


class UsuarioOut(ORMModel):
    id: int
    username: str
    first_name: str
    last_name: str
    email: str
    is_active: bool


class EmpleadoBase(BaseModel):
    ci: str
    nombre_completo: str
    direccion: str | None = None
    telefono: str | None = None
    sueldo: Decimal | None = Decimal("0")
    cargo: str | None = None
    roles: list[str] = Field(default_factory=list)


class EmpleadoCreate(EmpleadoBase):
    email: EmailStr


class EmpleadoInvitationActivateRequest(BaseModel):
    token: str
    username: str
    password: str


class EmpleadoUpdate(BaseModel):
    ci: str | None = None
    nombre_completo: str | None = None
    direccion: str | None = None
    telefono: str | None = None
    sueldo: Decimal | None = None
    cargo: str | None = None
    email: EmailStr | None = None
    roles: list[str] | None = None


class EmpleadoOut(ORMModel):
    id: str
    usuario: UsuarioOut
    ci: str
    nombre_completo: str
    direccion: str | None
    telefono: str | None
    sueldo: Decimal
    cargo: str | None
    empresa: str
    empresa_nombre: str | None = None
    foto_perfil: str | None
    latitud_actual: float | None = None
    longitud_actual: float | None = None
    disponible: bool = True
    roles_asignados: list[RoleOut]
    cargo_nombre: str | None
