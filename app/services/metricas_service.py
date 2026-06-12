"""Servicio de métricas y KPIs (Fase 2).

Calcula indicadores clave a partir de las tablas de incidentes,
asignaciones y empresas.  Todas las funciones aceptan un parámetro
opcional ``empresa_id`` para filtrar por taller (multi-tenant).
"""
from __future__ import annotations

import logging
from typing import Sequence

from sqlalchemy import Float, Numeric, and_, case, distinct, func
from sqlalchemy.orm import Session

from app.db.models import AsignacionServicio, Empresa, Incidente
from app.schemas.metrica_schema import (
    CasosCanceladosOut,
    DashboardMetricsOut,
    SolicitudesEnTiempoOut,
    TallerEficienteOut,
    TiempoPromedioOut,
    TipoIncidenteCount,
    ZonaIncidenteOut,
)

logger = logging.getLogger(__name__)

# Helper: minutos entre dos timestamps extraídos como epoch
def _epoch_minutes(ts_col):
    """Retorna expresión SQLAlchemy que calcula minutos entre epoch de dos columnas."""
    return func.extract("epoch", ts_col) / 60.0


# ============================================================
# 5.1 — Tiempo promedio de asignación (creado → asignado)
# ============================================================

def get_tiempo_promedio_asignacion(db: Session, empresa_id: str | None = None) -> TiempoPromedioOut:
    """Minutos promedio entre la creación del incidente y la asignación."""
    diff = (
        func.extract("epoch", AsignacionServicio.fecha_asignacion)
        - func.extract("epoch", Incidente.creado_en)
    ) / 60.0

    q = db.query(func.avg(diff), func.count()).join(
        Incidente, AsignacionServicio.incidente_id == Incidente.id
    ).filter(
        AsignacionServicio.fecha_asignacion.isnot(None),
        Incidente.creado_en.isnot(None),
    )
    if empresa_id:
        q = q.filter(AsignacionServicio.empresa_id == empresa_id)

    avg_val, total = q.one()
    return TiempoPromedioOut(
        minutos=round(float(avg_val), 2) if avg_val is not None else None,
        total_registros=total or 0,
    )


# ============================================================
# 5.2 — Tiempo promedio de llegada (asignado → cierre)
# ============================================================

def get_tiempo_promedio_llegada(db: Session, empresa_id: str | None = None) -> TiempoPromedioOut:
    """Minutos promedio entre la asignación y el cierre de la tarea."""
    diff = (
        func.extract("epoch", AsignacionServicio.fecha_cierre)
        - func.extract("epoch", AsignacionServicio.fecha_asignacion)
    ) / 60.0

    q = db.query(func.avg(diff), func.count()).filter(
        AsignacionServicio.fecha_cierre.isnot(None),
        AsignacionServicio.fecha_asignacion.isnot(None),
    )
    if empresa_id:
        q = q.filter(AsignacionServicio.empresa_id == empresa_id)

    avg_val, total = q.one()
    return TiempoPromedioOut(
        minutos=round(float(avg_val), 2) if avg_val is not None else None,
        total_registros=total or 0,
    )


# ============================================================
# 5.3 — Tipos de incidentes / solicitudes
# ============================================================

def get_tipos_incidentes(db: Session, empresa_id: str | None = None) -> list[TipoIncidenteCount]:
    """Conteo de incidentes agrupados por tipo."""
    q = db.query(
        Incidente.tipo,
        func.count().label("cantidad"),
    )
    if empresa_id:
        q = q.join(AsignacionServicio, AsignacionServicio.incidente_id == Incidente.id).filter(
            AsignacionServicio.empresa_id == empresa_id
        )

    q = q.group_by(Incidente.tipo).order_by(func.count().desc())
    rows = q.all()
    return [TipoIncidenteCount(tipo=r[0] or "Sin tipo", cantidad=r[1]) for r in rows]


# ============================================================
# 5.4 — Talleres más eficientes
# ============================================================

def get_talleres_eficientes(db: Session, limit: int = 10) -> list[TallerEficienteOut]:
    """Ranking de talleres por eficiencia (tiempo + rating)."""
    # Tiempo promedio de asignación por taller
    diff_assign = (
        func.extract("epoch", AsignacionServicio.fecha_asignacion)
        - func.extract("epoch", Incidente.creado_en)
    ) / 60.0

    diff_resolve = (
        func.extract("epoch", AsignacionServicio.fecha_cierre)
        - func.extract("epoch", AsignacionServicio.fecha_asignacion)
    ) / 60.0

    rows = (
        db.query(
            Empresa.id,
            Empresa.nombre,
            func.count(AsignacionServicio.id).label("total"),
            func.avg(diff_assign).label("avg_assign"),
            func.avg(diff_resolve).label("avg_resolve"),
            Empresa.estrellas_promedio,
        )
        .outerjoin(AsignacionServicio, AsignacionServicio.empresa_id == Empresa.id)
        .outerjoin(Incidente, AsignacionServicio.incidente_id == Incidente.id)
        .group_by(Empresa.id, Empresa.nombre, Empresa.estrellas_promedio)
        .all()
    )

    resultados: list[TallerEficienteOut] = []
    for r in rows:
        avg_assign = float(r.avg_assign) if r.avg_assign is not None else 0.0
        avg_resolve = float(r.avg_resolve) if r.avg_resolve is not None else 0.0
        rating = float(r.estrellas_promedio or 0)

        # Puntaje: 50% rating, 25% velocidad asignación, 25% velocidad resolución
        # Usamos 1/(1+minutos) para que menor tiempo = mayor puntaje
        score = (
            (rating / 5.0) * 0.50
            + (1.0 / (1.0 + avg_assign)) * 0.25
            + (1.0 / (1.0 + avg_resolve)) * 0.25
        )

        resultados.append(
            TallerEficienteOut(
                empresa_id=r.id,
                nombre=r.nombre,
                total_incidentes=r.total or 0,
                tiempo_promedio_asignacion_min=round(avg_assign, 2) if r.avg_assign else None,
                tiempo_promedio_resolucion_min=round(avg_resolve, 2) if r.avg_resolve else None,
                estrellas_promedio=rating,
                puntuacion_eficiencia=round(score, 4),
            )
        )

    resultados.sort(key=lambda t: t.puntuacion_eficiencia, reverse=True)
    return resultados[:limit]


# ============================================================
# 5.5 — Zonas con más incidentes
# ============================================================

def get_zonas_mas_incidentes(db: Session, limit: int = 10) -> list[ZonaIncidenteOut]:
    """Agrupa incidentes por zona geográfica (lat/lon redondeado a 2 decimales ≈ 1 km)."""
    lat_r = func.round(Incidente.latitud.cast(Numeric), 2)
    lon_r = func.round(Incidente.longitud.cast(Numeric), 2)

    rows = (
        db.query(
            lat_r.label("lat"),
            lon_r.label("lon"),
            func.count().label("cantidad"),
            func.array_agg(distinct(Incidente.tipo)).label("tipos"),
        )
        .filter(Incidente.latitud.isnot(None), Incidente.longitud.isnot(None))
        .group_by(lat_r, lon_r)
        .order_by(func.count().desc())
        .limit(limit)
        .all()
    )

    return [
        ZonaIncidenteOut(
            latitud_redondeada=float(r.lat),
            longitud_redondeada=float(r.lon),
            cantidad=r.cantidad,
            tipos=[t for t in (r.tipos or []) if t],
        )
        for r in rows
    ]


# ============================================================
# 5.6 — Casos cancelados
# ============================================================

def get_casos_cancelados(db: Session, empresa_id: str | None = None) -> CasosCanceladosOut:
    """Cuenta incidentes cancelados (por cliente o taller)."""
    total = db.query(func.count()).select_from(Incidente).scalar() or 0

    q_cancel = db.query(func.count()).select_from(Incidente).filter(
        Incidente.estado.in_(["cancelada", "cancelado"])
    )
    if empresa_id:
        q_cancel = q_cancel.filter(Incidente.accepted_empresa_id == empresa_id)
    cancelados = q_cancel.scalar() or 0

    # Cancelados que fueron aceptados por un taller pero luego cancelados
    q_taller = db.query(func.count()).select_from(Incidente).filter(
        Incidente.estado.in_(["cancelada", "cancelado"]),
        Incidente.accepted_empresa_id.isnot(None),
    )
    if empresa_id:
        q_taller = q_taller.filter(Incidente.accepted_empresa_id == empresa_id)
    cancel_taller = q_taller.scalar() or 0

    cancel_cliente = cancelados - cancel_taller
    porcentaje = round((cancelados / total * 100), 2) if total > 0 else 0.0

    return CasosCanceladosOut(
        total_cancelados=cancelados,
        cancelados_por_taller=cancel_taller,
        cancelados_por_cliente=cancel_cliente,
        porcentaje_cancelacion=porcentaje,
    )


# ============================================================
# 5.7 — Solicitudes atendidas dentro del tiempo esperado
# ============================================================

def get_solicitudes_en_tiempo(db: Session, empresa_id: str | None = None) -> SolicitudesEnTiempoOut:
    """Compara el tiempo real de atención con el estimado."""
    actual_min = (
        func.extract("epoch", AsignacionServicio.fecha_cierre)
        - func.extract("epoch", AsignacionServicio.fecha_asignacion)
    ) / 60.0

    base = db.query(AsignacionServicio).filter(
        AsignacionServicio.fecha_cierre.isnot(None),
        AsignacionServicio.fecha_asignacion.isnot(None),
        AsignacionServicio.tiempo_estimado_llegada_minutos.isnot(None),
    )
    if empresa_id:
        base = base.filter(AsignacionServicio.empresa_id == empresa_id)

    total = base.count()

    en_tiempo = base.filter(
        actual_min <= AsignacionServicio.tiempo_estimado_llegada_minutos
    ).count()

    porcentaje = round((en_tiempo / total * 100), 2) if total > 0 else 0.0

    return SolicitudesEnTiempoOut(
        total_asignadas=total,
        atendidas_en_tiempo=en_tiempo,
        porcentaje=porcentaje,
    )


# ============================================================
# Dashboard completo
# ============================================================

def get_dashboard_metrics(db: Session, empresa_id: str | None = None) -> DashboardMetricsOut:
    """Consolida todas las métricas en un solo objeto."""
    return DashboardMetricsOut(
        tiempo_promedio_asignacion=get_tiempo_promedio_asignacion(db, empresa_id),
        tiempo_promedio_llegada=get_tiempo_promedio_llegada(db, empresa_id),
        tipos_incidentes=get_tipos_incidentes(db, empresa_id),
        talleres_eficientes=get_talleres_eficientes(db),
        zonas_mas_incidentes=get_zonas_mas_incidentes(db),
        casos_cancelados=get_casos_cancelados(db, empresa_id),
        solicitudes_en_tiempo=get_solicitudes_en_tiempo(db, empresa_id),
    )
