from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from decimal import Decimal

from app.db.session import get_db
from app.deps.auth import get_current_user, resolve_tenant_empresa_id
from app.services.permission_service import resolve_employee
from app.services.pago_service import (
    create_pago,
    list_pagos,
    get_pago_or_404,
    confirmar_pago,
    rechazar_pago,
)
from app.db.models import Cliente
from app.schemas.pago import PagoCreate, PagoOut
from app.db.models import Pago as PagoModel

router = APIRouter()


@router.post("/api/asignaciones/{asignacion_id}/pago", response_model=PagoOut, status_code=status.HTTP_201_CREATED)
def crear_pago_asignacion(asignacion_id: str, payload: PagoCreate, user=Depends(get_current_user), db: Session = Depends(get_db)):
    pago = create_pago(db, asignacion_id=asignacion_id, monto_total=payload.monto_total, metodo_pago=payload.metodo_pago)
    return pago


@router.get("/api/pagos/", response_model=list[PagoOut])
def pagos_list(user=Depends(get_current_user), db: Session = Depends(get_db)):
    empleado = resolve_employee(db, user)
    if empleado:
        empresa_id = resolve_tenant_empresa_id(user, empleado)
        rows = list_pagos(db, empresa_id=empresa_id)
        return rows

    # try client
    stmt = select(Cliente).where(Cliente.usuario_id == user.id)
    cliente = db.execute(stmt).scalars().first()
    if cliente:
        rows = list_pagos(db, empresa_id=None)
        # filter by cliente_id
        return [p for p in rows if p.cliente_id == cliente.id]

    # fallback: return empty
    return []


@router.get("/api/pagos/{pago_id}", response_model=PagoOut)
def pagos_retrieve(pago_id: str, user=Depends(get_current_user), db: Session = Depends(get_db)):
    pago = get_pago_or_404(db, pago_id)
    return pago


@router.patch("/api/pagos/{pago_id}/confirmar", response_model=PagoOut)
def pagos_confirmar(pago_id: str, user=Depends(get_current_user), db: Session = Depends(get_db)):
    pago = get_pago_or_404(db, pago_id)
    pago = confirmar_pago(db, pago)
    return pago


@router.patch("/api/pagos/{pago_id}/rechazar", response_model=PagoOut)
def pagos_rechazar(pago_id: str, user=Depends(get_current_user), db: Session = Depends(get_db)):
    pago = get_pago_or_404(db, pago_id)
    pago = rechazar_pago(db, pago)
    return pago
