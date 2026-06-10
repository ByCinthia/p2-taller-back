from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import User, Cliente
from app.db.session import get_db
from app.deps.auth import get_current_user, require_permission
from app.schemas.cliente import ClienteOut, ClienteUpdate
from app.schemas.vehiculo import VehiculoCreate, VehiculoOut
from app.services.cliente_service import (
    list_clientes,
    get_cliente_for_user_or_404,
    get_cliente_or_404,
    get_cliente_historial,
    update_cliente,
    send_verification_sms,
    verify_sms,
)
from app.services.vehiculo_service import create_vehiculo_for_cliente, list_vehiculos_for_cliente


router = APIRouter(prefix="/api/clientes", tags=["clientes"])


@router.get("/", response_model=list[ClienteOut])
def clientes_list(db: Session = Depends(get_db)) -> list[ClienteOut]:
    return list_clientes(db)


@router.get("/me/", response_model=ClienteOut)
def clientes_me(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> ClienteOut:
    try:
        return get_cliente_for_user_or_404(db, user.id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado")


@router.put("/me/", response_model=ClienteOut)
def clientes_update_me(payload: ClienteUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> ClienteOut:
    try:
        cliente = get_cliente_for_user_or_404(db, user.id)
        return update_cliente(db, cliente, payload)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado")


@router.get("/me/vehiculos", response_model=list[VehiculoOut])
def cliente_list_my_vehiculos(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[VehiculoOut]:
    try:
        cliente = get_cliente_for_user_or_404(db, user.id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado")
    return list_vehiculos_for_cliente(db, cliente.id)


@router.post("/me/vehiculos", response_model=VehiculoOut, status_code=status.HTTP_201_CREATED)
def cliente_add_my_vehiculo(payload: VehiculoCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> VehiculoOut:
    try:
        cliente = get_cliente_for_user_or_404(db, user.id)
        return create_vehiculo_for_cliente(db, cliente.id, payload)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado")


@router.get("/me/vehiculos/{vehiculo_id}", response_model=VehiculoOut)
def clientes_me_get_vehiculo(vehiculo_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> VehiculoOut:
    try:
        from app.services.vehiculo_service import get_vehiculo_or_404
        v = get_vehiculo_or_404(db, vehiculo_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehiculo no encontrado")
    # ensure owner
    cliente = get_cliente_for_user_or_404(db, user.id)
    if str(v.cliente_id) != str(cliente.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehiculo no encontrado")
    return v


@router.delete("/me/vehiculos/{vehiculo_id}", status_code=status.HTTP_204_NO_CONTENT)
def clientes_me_delete_vehiculo(vehiculo_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        from app.services.vehiculo_service import get_vehiculo_or_404, delete_vehiculo
        v = get_vehiculo_or_404(db, vehiculo_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehiculo no encontrado")
    cliente = get_cliente_for_user_or_404(db, user.id)
    if str(v.cliente_id) != str(cliente.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehiculo no encontrado")
    delete_vehiculo(db, v)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me/vehiculos/count", response_model=dict)
def clientes_me_count_vehiculos(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    cliente = get_cliente_for_user_or_404(db, user.id)
    rows = list_vehiculos_for_cliente(db, cliente.id)
    return {"count": len(rows)}


@router.get("/{cliente_id}/", response_model=ClienteOut)
def clientes_retrieve(cliente_id: int, db: Session = Depends(get_db)) -> ClienteOut:
    try:
        return get_cliente_or_404(db, str(cliente_id))
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado")


@router.put("/{cliente_id}/", response_model=ClienteOut)
def clientes_update(cliente_id: int, payload: ClienteUpdate, user=Depends(require_permission("manage_clientes")), db: Session = Depends(get_db)) -> ClienteOut:
    try:
        cliente = get_cliente_or_404(db, str(cliente_id))
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado")
    return update_cliente(db, cliente, payload)


@router.get("/{cliente_id}/historial")
def clientes_historial(cliente_id: int, db: Session = Depends(get_db)):
    try:
        return get_cliente_historial(db, str(cliente_id))
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Historial no encontrado")


@router.post("/verificar-sms", status_code=status.HTTP_200_OK)
def clientes_verificar_sms(body: dict, db: Session = Depends(get_db)) -> dict:
    cliente_id = body.get("cliente_id")
    if not cliente_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="cliente_id requerido")

    code = body.get("code")
    if code is None:
        try:
            send_verification_sms(db, cliente_id)
        except Exception:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado")
        return {"status": "code_sent"}

    ok = verify_sms(db, cliente_id, str(code))
    return {"verified": ok}
