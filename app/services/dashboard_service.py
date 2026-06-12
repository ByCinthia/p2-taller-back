"""Servicio del Dashboard (Fase 3).

Proporciona consultas optimizadas para renderizar dashboards:
resumen con tarjetas, series temporales para gráficos, desglose
por estado, datos para mapas y rendimiento de talleres.

Todas las funciones aceptan filtros opcionales ``empresa_id``,
``desde`` y ``hasta`` para soporte multi-tenant y temporal.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Sequence

from sqlalchemy import Float, Date, cast, func, distinct
from sqlalchemy.orm import Session

from app.db.models import (
    AsignacionServicio,
    Cliente,
    Empleado,
    Empresa,
    Incidente,
)
from app.schemas.dashboard_schema import (
    DashboardCompletoOut,
    IncidentePorEstado,
    MapaIncidenteOut,
    PuntoSerieTemporal,
    RendimientoTallerOut,
    ResumenDashboard,
)
from app.services.metricas_service import (
    get_talleres_eficientes,
    get_tipos_incidentes,
    get_zonas_mas_incidentes,
)

logger = logging.getLogger(__name__)


# ============================================================
# Helpers
# ============================================================

def _apply_date_filter(query, model, desde: datetime | None, hasta: datetime | None):
    if desde:
        query = query.filter(model.creado_en >= desde)
    if hasta:
        query = query.filter(model.creado_en <= hasta)
    return query


def _parse_fecha(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return None


# ============================================================
# Resumen (tarjetas)
# ============================================================

def get_resumen(
    db: Session,
    empresa_id: str | None = None,
    desde: datetime | None = None,
    hasta: datetime | None = None,
) -> ResumenDashboard:
    q = db.query(Incidente)
    q = _apply_date_filter(q, Incidente, desde, hasta)

    total = q.count()

    def _count(estado: str) -> int:
        cq = q.filter(Incidente.estado == estado)
        if empresa_id:
            cq = cq.filter(Incidente.accepted_empresa_id == empresa_id)
        return cq.count()

    # Conteos por estado
    pendientes = _count("pendiente")
    aceptados = _count("aceptada")
    asignados = _count("asignada")
    en_proceso = _count("en_proceso")
    atendidos = _count("atendido")
    completados = _count("completada")
    cancelados = q.filter(Incidente.estado.in_(["cancelada", "cancelado"])).count()
    if empresa_id:
        cancelados = q.filter(
            Incidente.estado.in_(["cancelada", "cancelado"]),
            Incidente.accepted_empresa_id == empresa_id,
        ).count()

    # Totales de entidades
    talleres_q = db.query(func.count()).select_from(Empresa)
    if empresa_id:
        talleres_q = talleres_q.filter(Empresa.id == empresa_id)
    total_talleres = talleres_q.scalar() or 0
    total_clientes = db.query(func.count()).select_from(Cliente).scalar() or 0

    tecnicos_q = db.query(func.count()).select_from(Empleado).filter(
        Empleado.disponible == True  # noqa: E712
    )
    if empresa_id:
        tecnicos_q = tecnicos_q.filter(Empleado.empresa_id == empresa_id)
    total_tecnicos = tecnicos_q.scalar() or 0

    # Promedio de estrellas
    avg_stars = db.query(func.avg(Empresa.estrellas_promedio)).scalar()
    promedio = round(float(avg_stars), 2) if avg_stars else 0.0

    return ResumenDashboard(
        total_incidentes=total,
        incidentes_pendientes=pendientes,
        incidentes_aceptados=aceptados,
        incidentes_asignados=asignados,
        incidentes_en_proceso=en_proceso,
        incidentes_atendidos=atendidos,
        incidentes_completados=completados,
        incidentes_cancelados=cancelados,
        total_talleres=total_talleres,
        total_clientes=total_clientes,
        total_tecnicos=total_tecnicos,
        promedio_estrellas_talleres=promedio,
    )


# ============================================================
# Desglose por estado
# ============================================================

def get_incidentes_por_estado(
    db: Session,
    empresa_id: str | None = None,
    desde: datetime | None = None,
    hasta: datetime | None = None,
) -> list[IncidentePorEstado]:
    q = db.query(Incidente)
    q = _apply_date_filter(q, Incidente, desde, hasta)
    if empresa_id:
        q = q.filter(Incidente.accepted_empresa_id == empresa_id)

    total = q.count()
    if total == 0:
        return []

    rows = (
        db.query(Incidente.estado, func.count().label("cnt"))
        .group_by(Incidente.estado)
        .all()
    )

    # Aplicar mismos filtros
    filtered_rows = []
    fq = db.query(Incidente.estado, func.count().label("cnt"))
    fq = _apply_date_filter(fq, Incidente, desde, hasta)
    if empresa_id:
        fq = fq.filter(Incidente.accepted_empresa_id == empresa_id)
    filtered_rows = fq.group_by(Incidente.estado).all()

    total_filtered = sum(r.cnt for r in filtered_rows) or 1

    return [
        IncidentePorEstado(
            estado=r.estado or "sin_estado",
            cantidad=r.cnt,
            porcentaje=round(r.cnt / total_filtered * 100, 2),
        )
        for r in filtered_rows
    ]


# ============================================================
# Serie temporal
# ============================================================

def get_incidentes_por_fecha(
    db: Session,
    empresa_id: str | None = None,
    desde: datetime | None = None,
    hasta: datetime | None = None,
    intervalo: str = "day",
) -> list[PuntoSerieTemporal]:
    """Agrupa incidentes por fecha usando DATE_TRUNC de PostgreSQL.

    ``intervalo`` puede ser: day, week, month.
    """
    valid_intervals = {"day", "week", "month"}
    if intervalo not in valid_intervals:
        intervalo = "day"

    fecha_trunc = func.date_trunc(intervalo, Incidente.creado_en).label("fecha")

    q = db.query(fecha_trunc, func.count().label("cantidad"))
    q = _apply_date_filter(q, Incidente, desde, hasta)
    if empresa_id:
        q = q.filter(Incidente.accepted_empresa_id == empresa_id)

    q = q.group_by(fecha_trunc).order_by(fecha_trunc)

    rows = q.all()
    return [
        PuntoSerieTemporal(
            fecha=r.fecha.strftime("%Y-%m-%d") if r.fecha else "",
            cantidad=r.cantidad,
        )
        for r in rows
    ]


# ============================================================
# Datos para mapa
# ============================================================

def get_mapa_incidentes(
    db: Session,
    empresa_id: str | None = None,
    desde: datetime | None = None,
    hasta: datetime | None = None,
    limit: int = 500,
) -> list[MapaIncidenteOut]:
    q = db.query(Incidente).filter(
        Incidente.latitud.isnot(None),
        Incidente.longitud.isnot(None),
    )
    q = _apply_date_filter(q, Incidente, desde, hasta)
    if empresa_id:
        q = q.filter(Incidente.accepted_empresa_id == empresa_id)

    q = q.order_by(Incidente.creado_en.desc()).limit(limit)
    incidentes = q.all()

    resultados: list[MapaIncidenteOut] = []
    for inc in incidentes:
        # Buscar taller asignado
        taller_nombre = None
        if inc.accepted_empresa_id:
            emp = db.get(Empresa, inc.accepted_empresa_id)
            if emp:
                taller_nombre = emp.nombre

        # Buscar cliente
        cliente_nombre = None
        if inc.cliente_id:
            cli = db.get(Cliente, inc.cliente_id)
            if cli:
                cliente_nombre = cli.nombre

        resultados.append(
            MapaIncidenteOut(
                incidente_id=inc.id,
                tipo=inc.tipo,
                estado=inc.estado,
                latitud=float(inc.latitud),
                longitud=float(inc.longitud),
                creado_en=inc.creado_en.isoformat() if inc.creado_en else "",
                cliente_nombre=cliente_nombre,
                taller_nombre=taller_nombre,
            )
        )

    return resultados


# ============================================================
# Dashboard completo
# ============================================================

def get_dashboard_completo(
    db: Session,
    empresa_id: str | None = None,
    desde: datetime | None = None,
    hasta: datetime | None = None,
    intervalo: str = "day",
    limit_talleres: int = 10,
    limit_zonas: int = 10,
    limit_mapa: int = 500,
) -> DashboardCompletoOut:
    """Combina todas las vistas del dashboard en una sola respuesta."""
    return DashboardCompletoOut(
        resumen=get_resumen(db, empresa_id, desde, hasta),
        por_estado=get_incidentes_por_estado(db, empresa_id, desde, hasta),
        serie_temporal=get_incidentes_por_fecha(db, empresa_id, desde, hasta, intervalo),
        tipos_incidentes=[
            {"tipo": t.tipo, "cantidad": t.cantidad}
            for t in get_tipos_incidentes(db, empresa_id)
        ],
        zonas_mas_incidentes=[
            {"latitud": z.latitud_redondeada, "longitud": z.longitud_redondeada, "cantidad": z.cantidad, "tipos": z.tipos}
            for z in get_zonas_mas_incidentes(db, limit=limit_zonas)
        ],
        talleres_eficientes=[
            RendimientoTallerOut(
                empresa_id=t.empresa_id,
                nombre=t.nombre,
                total_solicitudes=t.total_incidentes,
                tiempo_promedio_asignacion_min=t.tiempo_promedio_asignacion_min,
                tiempo_promedio_resolucion_min=t.tiempo_promedio_resolucion_min,
                estrellas_promedio=t.estrellas_promedio,
                puntuacion_eficiencia=t.puntuacion_eficiencia,
            )
            for t in get_talleres_eficientes(db, limit=limit_talleres)
        ],
        mapa_incidentes=get_mapa_incidentes(db, empresa_id, desde, hasta, limit_mapa),
    )
