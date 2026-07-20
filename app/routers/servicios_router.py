import logging
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Empresa, User
from app.db.session import get_db
from app.deps.auth import get_current_user, require_permission
from app.schemas.servicio import ServicioCreate, ServicioOut, ServicioUpdate
from app.services.user_management import (
    _serialize_servicio,
    create_servicio,
    delete_servicio,
    get_servicio_or_404,
    list_servicios,
    update_servicio,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/servicios", tags=["servicios"])


def _check_empresa_id(user: User) -> str:
    empresa_id = user.empresa_id
    if not empresa_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso denegado. El usuario no está asociado a una empresa o taller."
        )
    return empresa_id


@router.get("/", response_model=list[ServicioOut])
def servicios_list(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ServicioOut]:
    empresa_id = _check_empresa_id(user)
    rows = list_servicios(db, empresa_id)
    logger.info(
        "Listando servicios - User ID: %s, Empresa ID: %s, Servicios encontrados: %d",
        user.id,
        empresa_id,
        len(rows),
    )
    return [_serialize_servicio(row) for row in rows]


@router.get("/{servicio_id}/", response_model=ServicioOut)
def servicios_retrieve(
    servicio_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ServicioOut:
    empresa_id = _check_empresa_id(user)
    servicio = get_servicio_or_404(db, servicio_id, empresa_id)
    return _serialize_servicio(servicio)


@router.post("/", response_model=ServicioOut, status_code=status.HTTP_201_CREATED)
def servicios_create(
    payload: ServicioCreate,
    user: User = Depends(require_permission("manage_servicio")),
    db: Session = Depends(get_db),
) -> ServicioOut:
    empresa_id = _check_empresa_id(user)
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
    empresa_id = _check_empresa_id(user)
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
    empresa_id = _check_empresa_id(user)
    servicio = get_servicio_or_404(db, servicio_id, empresa_id)
    delete_servicio(db, servicio)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
