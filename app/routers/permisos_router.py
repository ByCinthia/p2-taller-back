from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.db.models import User
from app.db.session import get_db
from app.deps.auth import get_current_user, require_permission
from app.schemas.permiso import PermisoCreate, PermisoOut, PermisoUpdate
from app.services.user_management import (
    create_permiso,
    delete_permiso,
    get_permiso_or_404,
    list_permisos,
    update_permiso,
)

router = APIRouter(prefix="/permisos", tags=["permisos"])


@router.get("/", response_model=list[PermisoOut])
def permisos_list(
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[PermisoOut]:
    return list_permisos(db)


@router.get("/{permiso_id}/", response_model=PermisoOut)
def permisos_retrieve(
    permiso_id: str,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PermisoOut:
    return get_permiso_or_404(db, permiso_id)


@router.post("/", response_model=PermisoOut, status_code=status.HTTP_201_CREATED)
def permisos_create(
    payload: PermisoCreate,
    _: User = Depends(require_permission("manage_permiso")),
    db: Session = Depends(get_db),
) -> PermisoOut:
    return create_permiso(db, nombre=payload.nombre, descripcion=payload.descripcion)


@router.put("/{permiso_id}/", response_model=PermisoOut)
@router.patch("/{permiso_id}/", response_model=PermisoOut)
def permisos_update(
    permiso_id: str,
    payload: PermisoUpdate,
    _: User = Depends(require_permission("manage_permiso")),
    db: Session = Depends(get_db),
) -> PermisoOut:
    permiso = get_permiso_or_404(db, permiso_id)
    return update_permiso(db, permiso, nombre=payload.nombre, descripcion=payload.descripcion)


@router.delete("/{permiso_id}/", status_code=status.HTTP_204_NO_CONTENT)
def permisos_delete(
    permiso_id: str,
    _: User = Depends(require_permission("manage_permiso")),
    db: Session = Depends(get_db),
) -> Response:
    permiso = get_permiso_or_404(db, permiso_id)
    delete_permiso(db, permiso)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
