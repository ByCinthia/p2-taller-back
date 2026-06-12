"""Schemas para el Dashboard de visualización (Fase 3).

Proporciona estructuras de datos optimizadas para renderizar
dashboards en el frontend: tarjetas de resumen, gráficos de
series temporales, desglose por estado, y datos para mapas.
"""
from __future__ import annotations

from pydantic import BaseModel


# ============================================================
# Tarjeta de resumen
# ============================================================

class ResumenDashboard(BaseModel):
    """Tarjetas de resumen para el dashboard."""
    total_incidentes: int = 0
    incidentes_pendientes: int = 0
    incidentes_aceptados: int = 0
    incidentes_asignados: int = 0
    incidentes_en_proceso: int = 0
    incidentes_atendidos: int = 0
    incidentes_completados: int = 0
    incidentes_cancelados: int = 0
    total_talleres: int = 0
    total_clientes: int = 0
    total_tecnicos: int = 0
    promedio_estrellas_talleres: float = 0.0


# ============================================================
# Desglose por estado
# ============================================================

class IncidentePorEstado(BaseModel):
    estado: str
    cantidad: int
    porcentaje: float = 0.0


# ============================================================
# Serie temporal (para gráficos de línea / barra)
# ============================================================

class PuntoSerieTemporal(BaseModel):
    fecha: str  # YYYY-MM-DD o YYYY-MM o YYYY-WNN
    cantidad: int


# ============================================================
# Datos para mapa
# ============================================================

class MapaIncidenteOut(BaseModel):
    incidente_id: str
    tipo: str | None = None
    estado: str
    latitud: float
    longitud: float
    creado_en: str  # ISO datetime
    cliente_nombre: str | None = None
    taller_nombre: str | None = None


# ============================================================
# Rendimiento de talleres (para tabla)
# ============================================================

class RendimientoTallerOut(BaseModel):
    empresa_id: str
    nombre: str
    total_solicitudes: int = 0
    solicitudes_aceptadas: int = 0
    solicitudes_atendidas: int = 0
    solicitudes_canceladas: int = 0
    tasa_aceptacion: float = 0.0
    tiempo_promedio_asignacion_min: float | None = None
    tiempo_promedio_resolucion_min: float | None = None
    estrellas_promedio: float = 0.0
    puntuacion_eficiencia: float = 0.0


# ============================================================
# Dashboard completo
# ============================================================

class DashboardCompletoOut(BaseModel):
    """Respuesta consolidada del dashboard para el frontend."""
    resumen: ResumenDashboard
    por_estado: list[IncidentePorEstado]
    serie_temporal: list[PuntoSerieTemporal]
    tipos_incidentes: list[dict]
    zonas_mas_incidentes: list[dict]
    talleres_eficientes: list[RendimientoTallerOut]
    mapa_incidentes: list[MapaIncidenteOut]
