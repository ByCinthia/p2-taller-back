from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import AsignacionServicio, Empleado, Incidente, Servicio


def create_asignacion(
    db: Session,
    incidente: Incidente,
    empleado_id: str,
    servicio_id: str | None = None,
    empresa_id: str | None = None,
    tiempo_estimado_llegada_minutos: int | None = None,
) -> AsignacionServicio:
    empleado = db.get(Empleado, empleado_id)
    if not empleado:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empleado no encontrado")

    # ensure we have a valid servicio_id (DB enforces FK and not-null)
    svc_id = servicio_id
    if not svc_id:
        # try to reuse an existing servicio for the empleado's empresa
        svc = db.execute(select(Servicio).where(Servicio.empresa_id == (empresa_id or empleado.empresa_id))).scalars().first()
        if svc:
            svc_id = svc.id_servicio
        else:
            # create a default servicio for this empresa to satisfy FK
            svc = Servicio(id_servicio=str(uuid.uuid4()), empresa_id=empresa_id or empleado.empresa_id, nombre='Servicio operativo (auto)', activo=True)
            db.add(svc)
            db.commit()
            db.refresh(svc)
            svc_id = svc.id_servicio

    obj = AsignacionServicio(
        id=str(uuid.uuid4()),
        incidente_id=incidente.id,
        empleado_id=empleado.id,
        servicio_id=svc_id,
        empresa_id=empresa_id or empleado.empresa_id,
        estado_tarea="asignada",
        tiempo_estimado_llegada_minutos=tiempo_estimado_llegada_minutos,
        fecha_asignacion=datetime.now(timezone.utc),
    )
    db.add(obj)
    # mark empleado as not disponible once assigned
    try:
        empleado.disponible = False
        db.add(empleado)
    except Exception:
        # non-fatal: proceed with creating assignment
        pass
    db.commit()
    db.refresh(obj)
    return obj


def get_active_asignacion_for_incidente(db: Session, incidente_id: str) -> AsignacionServicio | None:
    # use ORM query for robustness
    stmt = select(AsignacionServicio).where(
        AsignacionServicio.incidente_id == incidente_id,
        AsignacionServicio.estado_tarea.in_(["asignada", "aceptada", "en_proceso"]),
    ).limit(1)
    res = db.execute(stmt).scalars().first()
    return res


def get_active_asignacion_for_empleado(db: Session, empleado_id: str) -> AsignacionServicio | None:
    stmt = select(AsignacionServicio).where(
        AsignacionServicio.empleado_id == empleado_id,
        AsignacionServicio.estado_tarea.in_(["asignada", "aceptada", "en_proceso"]),
    ).limit(1)
    return db.execute(stmt).scalars().first()


def close_active_asignacion_for_incidente(db: Session, incidente_id: str) -> AsignacionServicio | None:
    asign = get_active_asignacion_for_incidente(db, incidente_id)
    if not asign:
        return None

    asign.estado_tarea = "atendido"
    asign.fecha_cierre = datetime.now(timezone.utc)

    empleado = db.get(Empleado, asign.empleado_id)
    if empleado:
        empleado.disponible = True
        db.add(empleado)

    db.add(asign)
    db.commit()
    db.refresh(asign)
    return asign


__all__ = [
    "create_asignacion",
    "get_active_asignacion_for_incidente",
    "get_active_asignacion_for_empleado",
    "close_active_asignacion_for_incidente",
]
