from pydantic import BaseModel

from app.schemas.common import ORMModel


class CargoBase(BaseModel):
    nombre: str
    descripcion: str | None = None


class CargoCreate(CargoBase):
    pass


class CargoUpdate(BaseModel):
    nombre: str | None = None
    descripcion: str | None = None


class CargoOut(ORMModel):
    id: str
    empresa: str
    nombre: str
    descripcion: str | None