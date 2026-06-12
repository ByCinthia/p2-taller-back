"""Router del Dashboard (Fase 3).

Endpoints para visualización de métricas en dashboard.
Soporta filtros por empresa, rango de fechas e intervalo temporal.
"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.tenant import TenantContext, get_tenant
from app.db.session import get_db
from app.deps.auth import get_current_user
from app.schemas.dashboard_schema import (
    DashboardCompletoOut,
    IncidentePorEstado,
    MapaIncidenteOut,
    PuntoSerieTemporal,
    RendimientoTallerOut,
    ResumenDashboard,
)
from app.services.dashboard_service import (
    get_dashboard_completo,
    get_incidentes_por_estado,
    get_incidentes_por_fecha,
    get_mapa_incidentes,
    get_resumen,
    _parse_fecha,
)
from app.services.metricas_service import get_talleres_eficientes

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _resolve_empresa_id(
    tenant: TenantContext,
    empresa_id_query: str | None,
) -> str | None:
    """Staff global puede filtrar por cualquier empresa; empleados se filtran automáticamente."""
    if tenant.empleado and not tenant.user.is_staff:
        return tenant.empresa_id
    return empresa_id_query


# ============================================================
# Dashboard completo
# ============================================================

@router.get("/", response_model=DashboardCompletoOut)
def dashboard_completo(
    empresa_id: str | None = Query(default=None, description="Filtrar por taller"),
    desde: str | None = Query(default=None, description="Fecha inicio (ISO: 2026-01-01)"),
    hasta: str | None = Query(default=None, description="Fecha fin (ISO: 2026-06-11)"),
    intervalo: str = Query(default="day", description="Agrupación temporal: day, week, month"),
    limit_talleres: int = Query(default=10, ge=1, le=50),
    limit_zonas: int = Query(default=10, ge=1, le=50),
    limit_mapa: int = Query(default=500, ge=1, le=2000),
    tenant: TenantContext = Depends(get_tenant),
    db: Session = Depends(get_db),
) -> DashboardCompletoOut:
    """Dashboard completo: resumen, series temporales, mapa, talleres, zonas.

    Combina todas las vistas en una sola respuesta para minimizar
    llamadas desde el frontend.
    """
    eid = _resolve_empresa_id(tenant, empresa_id)
    return get_dashboard_completo(
        db,
        empresa_id=eid,
        desde=_parse_fecha(desde),
        hasta=_parse_fecha(hasta),
        intervalo=intervalo,
        limit_talleres=limit_talleres,
        limit_zonas=limit_zonas,
        limit_mapa=limit_mapa,
    )


# ============================================================
# Vistas individuales
# ============================================================

@router.get("/resumen", response_model=ResumenDashboard)
def dashboard_resumen(
    empresa_id: str | None = Query(default=None),
    desde: str | None = Query(default=None),
    hasta: str | None = Query(default=None),
    tenant: TenantContext = Depends(get_tenant),
    db: Session = Depends(get_db),
) -> ResumenDashboard:
    """Tarjetas de resumen: totales, estados, talleres, clientes, técnicos."""
    eid = _resolve_empresa_id(tenant, empresa_id)
    return get_resumen(db, eid, _parse_fecha(desde), _parse_fecha(hasta))


@router.get("/por-estado", response_model=list[IncidentePorEstado])
def dashboard_por_estado(
    empresa_id: str | None = Query(default=None),
    desde: str | None = Query(default=None),
    hasta: str | None = Query(default=None),
    tenant: TenantContext = Depends(get_tenant),
    db: Session = Depends(get_db),
) -> list[IncidentePorEstado]:
    """Desglose de incidentes por estado (para gráfico de pastel)."""
    eid = _resolve_empresa_id(tenant, empresa_id)
    return get_incidentes_por_estado(db, eid, _parse_fecha(desde), _parse_fecha(hasta))


@router.get("/por-fecha", response_model=list[PuntoSerieTemporal])
def dashboard_por_fecha(
    empresa_id: str | None = Query(default=None),
    desde: str | None = Query(default=None),
    hasta: str | None = Query(default=None),
    intervalo: str = Query(default="day", description="day, week o month"),
    tenant: TenantContext = Depends(get_tenant),
    db: Session = Depends(get_db),
) -> list[PuntoSerieTemporal]:
    """Serie temporal de incidentes (para gráfico de línea/barras)."""
    eid = _resolve_empresa_id(tenant, empresa_id)
    return get_incidentes_por_fecha(db, eid, _parse_fecha(desde), _parse_fecha(hasta), intervalo)


@router.get("/mapa", response_model=list[MapaIncidenteOut])
def dashboard_mapa(
    empresa_id: str | None = Query(default=None),
    desde: str | None = Query(default=None),
    hasta: str | None = Query(default=None),
    limit: int = Query(default=500, ge=1, le=2000),
    tenant: TenantContext = Depends(get_tenant),
    db: Session = Depends(get_db),
) -> list[MapaIncidenteOut]:
    """Datos de incidentes con coordenadas para renderizar en mapa."""
    eid = _resolve_empresa_id(tenant, empresa_id)
    return get_mapa_incidentes(db, eid, _parse_fecha(desde), _parse_fecha(hasta), limit)


@router.get("/talleres", response_model=list[RendimientoTallerOut])
def dashboard_talleres(
    limit: int = Query(default=10, ge=1, le=50),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[RendimientoTallerOut]:
    """Ranking de talleres con métricas de rendimiento."""
    talleres = get_talleres_eficientes(db, limit=limit)
    return [
        RendimientoTallerOut(
            empresa_id=t.empresa_id,
            nombre=t.nombre,
            total_solicitudes=t.total_incidentes,
            solicitudes_aceptadas=0,
            solicitudes_atendidas=0,
            solicitudes_canceladas=0,
            tasa_aceptacion=0.0,
            tiempo_promedio_asignacion_min=t.tiempo_promedio_asignacion_min,
            tiempo_promedio_resolucion_min=t.tiempo_promedio_resolucion_min,
            estrellas_promedio=t.estrellas_promedio,
            puntuacion_eficiencia=t.puntuacion_eficiencia,
        )
        for t in talleres
    ]
