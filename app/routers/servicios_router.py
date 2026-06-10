from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Empresa, User
from app.db.session import get_db
from app.deps.auth import get_current_user, require_permission, resolve_tenant_empresa_id
from app.schemas.servicio import ServicioCreate, ServicioOut, ServicioUpdate
from app.services.permission_service import resolve_employee
from app.services.user_management import (
    _serialize_servicio,
    create_servicio,
    delete_servicio,
    get_servicio_or_404,
    list_servicios,
    update_servicio,
)

router = APIRouter(prefix="/servicios", tags=["servicios"])


def _resolve_target_empresa_id(db: Session, user: User) -> str:
    empleado = resolve_employee(db, user)
    empresa_id = resolve_tenant_empresa_id(user, empleado)
    if empresa_id:
        return empresa_id

    first_empresa = db.execute(select(Empresa).order_by(Empresa.fecha_creacion)).scalars().first()
    if not first_empresa:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No hay talleres registrados")
    return first_empresa.id


@router.get("/", response_model=list[ServicioOut])
def servicios_list(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ServicioOut]:
    empleado = resolve_employee(db, user)
    empresa_id = resolve_tenant_empresa_id(user, empleado)
    rows = list_servicios(db, empresa_id)
    return [_serialize_servicio(row) for row in rows]


@router.get("/{servicio_id}/", response_model=ServicioOut)
def servicios_retrieve(
    servicio_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ServicioOut:
    empleado = resolve_employee(db, user)
    empresa_id = resolve_tenant_empresa_id(user, empleado)
    servicio = get_servicio_or_404(db, servicio_id, empresa_id)
    return _serialize_servicio(servicio)


@router.post("/", response_model=ServicioOut, status_code=status.HTTP_201_CREATED)
def servicios_create(
    payload: ServicioCreate,
    user: User = Depends(require_permission("manage_servicio")),
    db: Session = Depends(get_db),
) -> ServicioOut:
    empresa_id = _resolve_target_empresa_id(db, user)
    servicio = create_servicio(
        db,
        empresa_id=empresa_id,
        nombre=payload.nombre,
        descripcion=payload.descripcion,
        activo=payload.activo,
    )
    return _serialize_servicio(servicio)


@router.put("/{servicio_id}/", response_model=ServicioOut)
@router.patch("/{servicio_id}/", response_model=ServicioOut)
def servicios_update(
    servicio_id: str,
    payload: ServicioUpdate,
    user: User = Depends(require_permission("manage_servicio")),
    db: Session = Depends(get_db),
) -> ServicioOut:
    empleado = resolve_employee(db, user)
    empresa_id = resolve_tenant_empresa_id(user, empleado)
    servicio = get_servicio_or_404(db, servicio_id, empresa_id)
    servicio = update_servicio(
        db,
        servicio,
        nombre=payload.nombre,
        descripcion=payload.descripcion,
        activo=payload.activo,
    )
    return _serialize_servicio(servicio)


@router.delete("/{servicio_id}/", status_code=status.HTTP_204_NO_CONTENT)
def servicios_delete(
    servicio_id: str,
    user: User = Depends(require_permission("manage_servicio")),
    db: Session = Depends(get_db),
) -> Response:
    empleado = resolve_employee(db, user)
    empresa_id = resolve_tenant_empresa_id(user, empleado)
    servicio = get_servicio_or_404(db, servicio_id, empresa_id)
    delete_servicio(db, servicio)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
