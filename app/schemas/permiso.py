from pydantic import BaseModel

from app.schemas.common import ORMModel


class PermisoBase(BaseModel):
    nombre: str
    descripcion: str


class PermisoCreate(PermisoBase):
    pass


class PermisoUpdate(BaseModel):
    nombre: str | None = None
    descripcion: str | None = None


class PermisoOut(ORMModel):
    id: str
    nombre: str
    descripcion: str
