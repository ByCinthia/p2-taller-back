from datetime import datetime

from pydantic import BaseModel, Field
from app.schemas.common import ORMModel
from typing import List


class IncidenteCreate(BaseModel):
    vehiculo_id: str | None = None
    tipo: str | None = None
    descripcion: str | None = None
    prioridad: int | None = None
    latitud: float | None = Field(default=None, ge=-90, le=90)
    longitud: float | None = Field(default=None, ge=-180, le=180)


class IncidenteUpdate(BaseModel):
    estado: str | None = None
    prioridad: int | None = None
    descripcion: str | None = None
    # tiempo_estimado ahora pertenece a la asignación operativa (asignacion_servicio)



class AsignarTecnicoRequest(BaseModel):
    empleado_id: str | None = None
    servicio_id: str | None = None


class TecnicoUbicacionUpdate(BaseModel):
    latitud: float = Field(ge=-90, le=90)
    longitud: float = Field(ge=-180, le=180)
    disponible: bool | None = None


class TecnicoCercanoOut(BaseModel):
    empleado_id: str
    nombre_completo: str
    latitud: float
    longitud: float
    distancia_km: float
    disponible: bool


class IncidenteTrackingOut(BaseModel):
    incidente_id: str
    estado: str
    latitud_incidente: float | None
    longitud_incidente: float | None
    asignacion_id: str | None
    empleado_id: str | None
    tecnico_nombre: str | None
    tecnico_latitud: float | None
    tecnico_longitud: float | None
    tecnico_disponible: bool | None
    tecnico_ubicacion_actualizada_en: str | None


class EvidenciaOut(ORMModel):
    id: str
    incidente_id: str
    tipo: str
    url_archivo: str | None
    texto: str | None


class DiagnosticoOut(ORMModel):
    id: str
    incidente_id: str
    clasificacion: int | None
    resumen: str | None
    prioridad: int | None
    creado_en: datetime


class IncidenteOut(ORMModel):
    id: str
    cliente_id: str | None
    vehiculo_id: str | None
    tipo: str | None
    descripcion: str | None
    estado: str
    accepted_empresa_id: str | None = None
    prioridad: int | None
    latitud: float | None
    longitud: float | None
    # assignment fields moved to asignacion_servicio
    creado_en: datetime
    evidencias: List[EvidenciaOut] | None = []
    diagnosticos: List[DiagnosticoOut] | None = []

class IncidentePatchEstado(BaseModel):
    """para actualizar SOLO el estado (usado en móvil)"""
    estado: str
    latitud: float | None = None
    longitud: float | None = None
