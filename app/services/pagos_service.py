from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Pago, AsignacionServicio, Incidente, Cliente, Empresa


def create_pago(db: Session, asignacion_id: str, monto_total: Decimal | None, metodo_pago: str) -> Pago:
    asignacion = db.get(AsignacionServicio, asignacion_id)
    if not asignacion:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asignación no encontrada")

    incidente_id = asignacion.incidente_id
    empresa_id = asignacion.empresa_id
    incidente = None
    cliente_id = None
    if incidente_id:
        incidente = db.get(Incidente, incidente_id)
        if incidente:
            cliente_id = incidente.cliente_id

    # determine amount
    if monto_total is None:
        if asignacion.costo_servicio is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se proporcionó monto y la asignación no tiene costo")
        monto = Decimal(asignacion.costo_servicio)
    else:
        monto = Decimal(monto_total)

    comision = (monto * Decimal("0.10")).quantize(Decimal("0.01"))
    monto_taller = (monto - comision).quantize(Decimal("0.01"))

    pago = Pago(
        id=str(uuid.uuid4()),
        asignacion_id=asignacion_id,
        incidente_id=incidente_id,
        cliente_id=cliente_id,
        empresa_id=empresa_id,
        monto_total=monto,
        metodo_pago=metodo_pago,
        estado="pendiente",
        comision_plataforma=comision,
        monto_taller=monto_taller,
        fecha_creacion=datetime.now(timezone.utc),
        fecha_confirmacion=None,
    )

    # For simulated immediate methods, mark as paid
    if metodo_pago in ("qr_simulado", "tarjeta_simulada"):
        pago.estado = "pagado"
        pago.fecha_confirmacion = datetime.now(timezone.utc)

    db.add(pago)
    db.commit()
    db.refresh(pago)
    return pago


def list_pagos(db: Session, empresa_id: str | None = None) -> list[Pago]:
    stmt = select(Pago)
    if empresa_id:
        stmt = stmt.where(Pago.empresa_id == empresa_id)
    return db.execute(stmt.order_by(Pago.fecha_creacion.desc())).scalars().all()


def get_pago_or_404(db: Session, pago_id: str) -> Pago:
    pago = db.get(Pago, pago_id)
    if not pago:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pago no encontrado")
    return pago


def confirmar_pago(db: Session, pago: Pago) -> Pago:
    if pago.estado == "pagado":
        return pago
    pago.estado = "pagado"
    pago.fecha_confirmacion = datetime.now(timezone.utc)
    db.add(pago)
    db.commit()
    db.refresh(pago)
    return pago


def rechazar_pago(db: Session, pago: Pago) -> Pago:
    if pago.estado == "rechazado":
        return pago
    pago.estado = "rechazado"
    db.add(pago)
    db.commit()
    db.refresh(pago)
    return pago
