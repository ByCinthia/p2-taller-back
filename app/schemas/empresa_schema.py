from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Optional


class EmpresaOut(BaseModel):
    id: str
    nombre: str
    nit: str
    direccion: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    estrellas_promedio: float = Field(default=5.0, ge=1.0, le=5.0)
    total_calificaciones: int = 0

    class Config:
        from_attributes = True


class EmpresaUbicacionUpdate(BaseModel):
    latitud: float = Field(..., ge=-90.0, le=90.0)
    longitud: float = Field(..., ge=-180.0, le=180.0)
