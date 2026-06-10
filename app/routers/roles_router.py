from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Empresa, User
from app.db.session import get_db
from app.deps.auth import get_current_user, require_permission, resolve_tenant_empresa_id
from app.schemas.role import RoleCreate, RoleOut, RoleUpdate
from app.services.permission_service import resolve_employee
from app.services.user_management import (
    _serialize_role,
    create_role,
    delete_role,
    get_role_or_404,
    list_roles,
    update_role,
)

router = APIRouter(prefix="/roles", tags=["roles"])


def _resolve_target_empresa_id(db: Session, user: User) -> str:
    empleado = resolve_employee(db, user)
    empresa_id = resolve_tenant_empresa_id(user, empleado)
    if empresa_id:
        return empresa_id

    first_empresa = db.execute(select(Empresa).order_by(Empresa.fecha_creacion)).scalars().first()
    if not first_empresa:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No hay talleres registrados")
    return first_empresa.id


@router.get("/", response_model=list[RoleOut])
def roles_list(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[RoleOut]:
    empleado = resolve_employee(db, user)
    empresa_id = resolve_tenant_empresa_id(user, empleado)
    rows = list_roles(db, empresa_id)
    return [_serialize_role(r) for r in rows]


@router.get("/{role_id}/", response_model=RoleOut)
def roles_retrieve(
    role_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RoleOut:
    empleado = resolve_employee(db, user)
    empresa_id = resolve_tenant_empresa_id(user, empleado)
    role = get_role_or_404(db, role_id, empresa_id)
    return _serialize_role(role)


@router.post("/", response_model=RoleOut, status_code=status.HTTP_201_CREATED)
def roles_create(
    payload: RoleCreate,
    user: User = Depends(require_permission("manage_rol")),
    db: Session = Depends(get_db),
) -> RoleOut:
    empresa_id = _resolve_target_empresa_id(db, user)
    role = create_role(db, empresa_id=empresa_id, nombre=payload.nombre, permission_ids=payload.permisos)
    return _serialize_role(role)


@router.put("/{role_id}/", response_model=RoleOut)
@router.patch("/{role_id}/", response_model=RoleOut)
def roles_update(
    role_id: str,
    payload: RoleUpdate,
    user: User = Depends(require_permission("manage_rol")),
    db: Session = Depends(get_db),
) -> RoleOut:
    empleado = resolve_employee(db, user)
    empresa_id = resolve_tenant_empresa_id(user, empleado)
    role = get_role_or_404(db, role_id, empresa_id)
    role = update_role(db, role, nombre=payload.nombre, permission_ids=payload.permisos)
    return _serialize_role(role)


@router.delete("/{role_id}/", status_code=status.HTTP_204_NO_CONTENT)
def roles_delete(
    role_id: str,
    user: User = Depends(require_permission("manage_rol")),
    db: Session = Depends(get_db),
) -> Response:
    empleado = resolve_employee(db, user)
    empresa_id = resolve_tenant_empresa_id(user, empleado)
    role = get_role_or_404(db, role_id, empresa_id)
    delete_role(db, role)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
