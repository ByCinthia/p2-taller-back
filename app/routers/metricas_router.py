"""Router de métricas y KPIs (Fase 2).

Expone endpoints REST para consultar cada KPI individualmente
y un endpoint de dashboard que consolida todas las métricas.
Todos los endpoints aceptan un filtro opcional ``empresa_id``
para soporte multi-tenant.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.tenant import TenantContext, get_tenant
from app.db.session import get_db
from app.deps.auth import get_current_user
from app.schemas.metrica_schema import (
    CasosCanceladosOut,
    DashboardMetricsOut,
    SolicitudesEnTiempoOut,
    TallerEficienteOut,
    TiempoPromedioOut,
    TipoIncidenteCount,
    ZonaIncidenteOut,
)
from app.services.metricas_service import (
    get_casos_cancelados,
    get_dashboard_metrics,
    get_solicitudes_en_tiempo,
    get_talleres_eficientes,
    get_tiempo_promedio_asignacion,
    get_tiempo_promedio_llegada,
    get_tipos_incidentes,
    get_zonas_mas_incidentes,
)

router = APIRouter(prefix="/metricas", tags=["metricas"])


def _resolve_empresa_id(
    tenant: TenantContext,
    empresa_id_query: str | None,
) -> str | None:
    """Si el usuario es staff global, permite filtrar por cualquier empresa
    mediante query param.  Si es empleado normal, ignora el param y usa
    su propio empresa_id."""
    if tenant.empleado and not tenant.user.is_staff:
        return tenant.empresa_id
    return empresa_id_query  # staff puede pasar None → global


# ============================================================
# Endpoints individuales por KPI
# ============================================================

@router.get("/tiempo-asignacion", response_model=TiempoPromedioOut)
def tiempo_promedio_asignacion(
    empresa_id: str | None = Query(default=None, description="Filtrar por taller"),
    tenant: TenantContext = Depends(get_tenant),
    db: Session = Depends(get_db),
) -> TiempoPromedioOut:
    """5.1 — Tiempo promedio de asignación (minutos entre creación y asignación)."""
    eid = _resolve_empresa_id(tenant, empresa_id)
    return get_tiempo_promedio_asignacion(db, empresa_id=eid)


@router.get("/tiempo-llegada", response_model=TiempoPromedioOut)
def tiempo_promedio_llegada(
    empresa_id: str | None = Query(default=None, description="Filtrar por taller"),
    tenant: TenantContext = Depends(get_tenant),
    db: Session = Depends(get_db),
) -> TiempoPromedioOut:
    """5.2 — Tiempo promedio de llegada (minutos entre asignación y cierre)."""
    eid = _resolve_empresa_id(tenant, empresa_id)
    return get_tiempo_promedio_llegada(db, empresa_id=eid)


@router.get("/tipos-incidentes", response_model=list[TipoIncidenteCount])
def tipos_incidentes(
    empresa_id: str | None = Query(default=None, description="Filtrar por taller"),
    tenant: TenantContext = Depends(get_tenant),
    db: Session = Depends(get_db),
) -> list[TipoIncidenteCount]:
    """5.3 — Conteo de incidentes agrupados por tipo."""
    eid = _resolve_empresa_id(tenant, empresa_id)
    return get_tipos_incidentes(db, empresa_id=eid)


@router.get("/talleres-eficientes", response_model=list[TallerEficienteOut])
def talleres_eficientes(
    limit: int = Query(default=10, ge=1, le=50),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[TallerEficienteOut]:
    """5.4 — Ranking de talleres más eficientes (tiempo + puntuación)."""
    return get_talleres_eficientes(db, limit=limit)


@router.get("/zonas-incidentes", response_model=list[ZonaIncidenteOut])
def zonas_mas_incidentes(
    limit: int = Query(default=10, ge=1, le=50),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ZonaIncidenteOut]:
    """5.5 — Zonas geográficas con más incidentes."""
    return get_zonas_mas_incidentes(db, limit=limit)


@router.get("/cancelados", response_model=CasosCanceladosOut)
def casos_cancelados(
    empresa_id: str | None = Query(default=None, description="Filtrar por taller"),
    tenant: TenantContext = Depends(get_tenant),
    db: Session = Depends(get_db),
) -> CasosCanceladosOut:
    """5.6 — Casos cancelados (por taller o por cliente)."""
    eid = _resolve_empresa_id(tenant, empresa_id)
    return get_casos_cancelados(db, empresa_id=eid)


@router.get("/solicitudes-en-tiempo", response_model=SolicitudesEnTiempoOut)
def solicitudes_en_tiempo(
    empresa_id: str | None = Query(default=None, description="Filtrar por taller"),
    tenant: TenantContext = Depends(get_tenant),
    db: Session = Depends(get_db),
) -> SolicitudesEnTiempoOut:
    """5.7 — Porcentaje de solicitudes atendidas dentro del tiempo estimado."""
    eid = _resolve_empresa_id(tenant, empresa_id)
    return get_solicitudes_en_tiempo(db, empresa_id=eid)


# ============================================================
# Dashboard consolidado
# ============================================================

@router.get("/dashboard", response_model=DashboardMetricsOut)
def dashboard(
    empresa_id: str | None = Query(default=None, description="Filtrar por taller"),
    tenant: TenantContext = Depends(get_tenant),
    db: Session = Depends(get_db),
) -> DashboardMetricsOut:
    """Dashboard completo: consolida todos los KPIs en una sola respuesta.

    Si se pasa ``empresa_id`` (o el usuario pertenece a un taller),
    las métricas se filtran por ese taller.  Si no, se muestran
    métricas globales de toda la plataforma.
    """
    eid = _resolve_empresa_id(tenant, empresa_id)
    return get_dashboard_metrics(db, empresa_id=eid)
