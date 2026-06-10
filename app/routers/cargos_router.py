from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Empresa, User
from app.db.session import get_db
from app.deps.auth import get_current_user, require_permission, resolve_tenant_empresa_id
from app.schemas.cargo import CargoCreate, CargoOut, CargoUpdate
from app.services.permission_service import resolve_employee
from app.services.user_management import (
    _serialize_cargo,
    create_cargo,
    delete_cargo,
    get_cargo_or_404,
    list_cargos,
    update_cargo,
)

router = APIRouter(prefix="/cargos", tags=["cargos"])


def _resolve_target_empresa_id(db: Session, user: User) -> str:
    empleado = resolve_employee(db, user)
    empresa_id = resolve_tenant_empresa_id(user, empleado)
    if empresa_id:
        return empresa_id

    first_empresa = db.execute(select(Empresa).order_by(Empresa.fecha_creacion)).scalars().first()
    if not first_empresa:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No hay talleres registrados")
    return first_empresa.id


@router.get("/", response_model=list[CargoOut])
def cargos_list(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[CargoOut]:
    empleado = resolve_employee(db, user)
    empresa_id = resolve_tenant_empresa_id(user, empleado)
    rows = list_cargos(db, empresa_id)
    return [_serialize_cargo(row) for row in rows]


@router.get("/{cargo_id}/", response_model=CargoOut)
def cargos_retrieve(
    cargo_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CargoOut:
    empleado = resolve_employee(db, user)
    empresa_id = resolve_tenant_empresa_id(user, empleado)
    cargo = get_cargo_or_404(db, cargo_id, empresa_id)
    return _serialize_cargo(cargo)


@router.post("/", response_model=CargoOut, status_code=status.HTTP_201_CREATED)
def cargos_create(
    payload: CargoCreate,
    user: User = Depends(require_permission("manage_cargo")),
    db: Session = Depends(get_db),
) -> CargoOut:
    empresa_id = _resolve_target_empresa_id(db, user)
    cargo = create_cargo(db, empresa_id=empresa_id, nombre=payload.nombre, descripcion=payload.descripcion)
    return _serialize_cargo(cargo)


@router.put("/{cargo_id}/", response_model=CargoOut)
@router.patch("/{cargo_id}/", response_model=CargoOut)
def cargos_update(
    cargo_id: str,
    payload: CargoUpdate,
    user: User = Depends(require_permission("manage_cargo")),
    db: Session = Depends(get_db),
) -> CargoOut:
    empleado = resolve_employee(db, user)
    empresa_id = resolve_tenant_empresa_id(user, empleado)
    cargo = get_cargo_or_404(db, cargo_id, empresa_id)
    cargo = update_cargo(db, cargo, nombre=payload.nombre, descripcion=payload.descripcion)
    return _serialize_cargo(cargo)


@router.delete("/{cargo_id}/", status_code=status.HTTP_204_NO_CONTENT)
def cargos_delete(
    cargo_id: str,
    user: User = Depends(require_permission("manage_cargo")),
    db: Session = Depends(get_db),
) -> Response:
    empleado = resolve_employee(db, user)
    empresa_id = resolve_tenant_empresa_id(user, empleado)
    cargo = get_cargo_or_404(db, cargo_id, empresa_id)
    delete_cargo(db, cargo)
    return Response(status_code=status.HTTP_204_NO_CONTENT)