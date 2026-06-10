from pydantic import BaseModel, Field

from app.schemas.common import ORMModel
from app.schemas.permiso import PermisoOut


class RoleBase(BaseModel):
    nombre: str
    permisos: list[str] = Field(default_factory=list)


class RoleCreate(RoleBase):
    pass


class RoleUpdate(BaseModel):
    nombre: str | None = None
    permisos: list[str] | None = None


class RoleOut(ORMModel):
    id: str
    empresa: str
    nombre: str
    permisos: list[PermisoOut]
