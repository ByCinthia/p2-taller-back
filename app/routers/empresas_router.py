from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.session import get_db
from app.deps.auth import get_current_user
from app.db.models import Empleado, Empresa
from app.schemas.empresa import EmpresaOut, EmpresaUbicacionUpdate
from app.services.permission_service import resolve_employee

router = APIRouter(prefix="/empresa", tags=["Empresa"]) 


@router.get("/me", response_model=EmpresaOut)
def empresa_me(user = Depends(get_current_user), db: Session = Depends(get_db)) -> EmpresaOut:
    empleado = resolve_employee(db, user)
    if not empleado:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empleado (taller) no encontrado para el usuario")

    empresa = db.get(Empresa, empleado.empresa_id)
    if not empresa:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empresa no encontrada")

    return empresa


@router.patch("/me/ubicacion", response_model=EmpresaOut)
def empresa_update_ubicacion(payload: EmpresaUbicacionUpdate, user = Depends(get_current_user), db: Session = Depends(get_db)) -> EmpresaOut:
    empleado = resolve_employee(db, user)
    if not empleado:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empleado (taller) no encontrado para el usuario")

    empresa = db.get(Empresa, empleado.empresa_id)
    if not empresa:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empresa no encontrada")

    empresa.latitud = payload.latitud
    empresa.longitud = payload.longitud
    db.add(empresa)
    db.commit()
    db.refresh(empresa)
    return empresa
