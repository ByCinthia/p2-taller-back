from pydantic import BaseModel

from app.schemas.common import ORMModel


class ServicioBase(BaseModel):
    nombre: str
    descripcion: str | None = None
    activo: bool = True


class ServicioCreate(ServicioBase):
    pass


class ServicioUpdate(BaseModel):
    nombre: str | None = None
    descripcion: str | None = None
    activo: bool | None = None


class ServicioOut(ORMModel):
    id_servicio: str
    nombre: str
    descripcion: str | None
    activo: bool
