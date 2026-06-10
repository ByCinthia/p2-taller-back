from pydantic import BaseModel, EmailStr

from app.schemas.common import ORMModel


class ClienteBase(BaseModel):
    nombre: str
    email: EmailStr | None = None
    telefono: str | None = None
    activo: bool | None = True


class ClienteCreate(ClienteBase):
    username: str
    password: str

class ClienteUpdate(BaseModel):
    nombre: str | None = None
    username: str | None = None
    password: str | None = None
    email: EmailStr | None = None
    telefono: str | None = None
    activo: bool | None = None


class ClienteOut(ORMModel):
    id: str
    nombre: str
    username: str | None
    email: str | None
    telefono: str | None
    activo: bool
