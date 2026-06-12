"""Schemas para los KPIs y métricas del dashboard."""
from __future__ import annotations

from pydantic import BaseModel


# ============================================================
# 5.1 — Tiempo promedio de asignación
# ============================================================

class TiempoPromedioOut(BaseModel):
    """Resultado de un cálculo de tiempo promedio."""
    minutos: float | None = None
    total_registros: int = 0


# ============================================================
# 5.3 — Tipos de incidentes
# ============================================================

class TipoIncidenteCount(BaseModel):
    tipo: str | None = None
    cantidad: int = 0


# ============================================================
# 5.4 — Talleres más eficientes
# ============================================================

class TallerEficienteOut(BaseModel):
    empresa_id: str
    nombre: str
    total_incidentes: int = 0
    tiempo_promedio_asignacion_min: float | None = None
    tiempo_promedio_resolucion_min: float | None = None
    estrellas_promedio: float = 0.0
    puntuacion_eficiencia: float = 0.0


# ============================================================
# 5.5 — Zonas con más incidentes
# ============================================================

class ZonaIncidenteOut(BaseModel):
    latitud_redondeada: float
    longitud_redondeada: float
    cantidad: int = 0
    tipos: list[str] = []


# ============================================================
# 5.6 — Casos cancelados
# ============================================================

class CasosCanceladosOut(BaseModel):
    total_cancelados: int = 0
    cancelados_por_taller: int = 0
    cancelados_por_cliente: int = 0
    porcentaje_cancelacion: float = 0.0


# ============================================================
# 5.7 — Solicitudes atendidas en tiempo esperado
# ============================================================

class SolicitudesEnTiempoOut(BaseModel):
    total_asignadas: int = 0
    atendidas_en_tiempo: int = 0
    porcentaje: float = 0.0


# ============================================================
# Dashboard completo
# ============================================================

class DashboardMetricsOut(BaseModel):
    """Todas las métricas consolidadas para el dashboard."""
    tiempo_promedio_asignacion: TiempoPromedioOut
    tiempo_promedio_llegada: TiempoPromedioOut
    tipos_incidentes: list[TipoIncidenteCount]
    talleres_eficientes: list[TallerEficienteOut]
    zonas_mas_incidentes: list[ZonaIncidenteOut]
    casos_cancelados: CasosCanceladosOut
    solicitudes_en_tiempo: SolicitudesEnTiempoOut
