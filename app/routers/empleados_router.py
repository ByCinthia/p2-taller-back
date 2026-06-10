from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request, Response, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import AsignacionServicio, Empresa, Servicio, User
from app.db.session import get_db
from app.deps.auth import get_base_url, get_current_user, require_permission, resolve_tenant_empresa_id
from app.schemas.empleado import MiAsignacionOut
from app.schemas.empleado import EmpleadoCreate, EmpleadoOut, EmpleadoUpdate
from app.services.file_storage import save_profile_image
from app.services.permission_service import resolve_employee
from app.services.user_management import (
    _serialize_empleado,
    create_empleado,
    delete_empleado,
    get_empleado_or_404,
    list_empleados,
    update_empleado,
)

router = APIRouter(prefix="/empleados", tags=["empleados"])


def _parse_bool(value: str | bool | None) -> bool | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    return value.lower() in {"1", "true", "yes", "on"}


def _resolve_create_payload_from_form(form_data) -> EmpleadoCreate:
    roles = [str(v) for v in form_data.getlist("roles") if str(v).strip()]
    sueldo_raw = form_data.get("sueldo")

    return EmpleadoCreate(
        nombre_completo=str(form_data.get("nombre_completo", "")),
        email=str(form_data.get("email", "")),
        ci=str(form_data.get("ci", "")),
        direccion=form_data.get("direccion") or None,
        telefono=form_data.get("telefono") or None,
        sueldo=Decimal(str(sueldo_raw)) if sueldo_raw not in (None, "") else Decimal("0"),
        cargo=form_data.get("cargo") or None,
        roles=roles,
    )


def _resolve_update_payload_from_form(form_data) -> EmpleadoUpdate:
    update_data = {}

    for field in [
        "ci",
        "nombre_completo",
        "direccion",
        "telefono",
        "cargo",
        "email",
    ]:
        if field in form_data:
            raw = form_data.get(field)
            update_data[field] = raw if raw != "" else None

    if "sueldo" in form_data:
        sueldo_raw = form_data.get("sueldo")
        update_data["sueldo"] = Decimal(str(sueldo_raw)) if sueldo_raw not in (None, "") else Decimal("0")

    if "roles" in form_data:
        update_data["roles"] = [str(v) for v in form_data.getlist("roles") if str(v).strip()]

    return EmpleadoUpdate(**update_data)


def _parse_payload(request: Request) -> str:
    content_type = request.headers.get("content-type", "")

    if "multipart/form-data" in content_type:
        return "form"
    if "application/json" in content_type:
        return "json"

    raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Content-Type no soportado")


def _resolve_target_empresa_id(db: Session, user: User) -> str:
    empleado = resolve_employee(db, user)
    empresa_id = resolve_tenant_empresa_id(user, empleado)
    if empresa_id:
        return empresa_id

    first_empresa = db.execute(select(Empresa).order_by(Empresa.fecha_creacion)).scalars().first()
    if not first_empresa:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No hay talleres registrados")
    return first_empresa.id


@router.get("/", response_model=list[EmpleadoOut])
def empleados_list(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[EmpleadoOut]:
    empleado = resolve_employee(db, user)
    empresa_id = resolve_tenant_empresa_id(user, empleado)
    rows = list_empleados(db, empresa_id, exclude_user_id=user.id, exclude_admin_roles=True)
    base_url = get_base_url(request)
    return [_serialize_empleado(row, base_url) for row in rows]


@router.get("/me/", response_model=EmpleadoOut)
def empleados_me(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EmpleadoOut:
    empleado = resolve_employee(db, user)
    if not empleado:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="El usuario no está asociado a un empleado")
    return _serialize_empleado(empleado, get_base_url(request))


@router.get("/me/asignaciones", response_model=list[MiAsignacionOut])
def empleados_mis_asignaciones(
        user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
) -> list[MiAsignacionOut]:
        empleado = resolve_employee(db, user)
        empresa_id = resolve_tenant_empresa_id(user, empleado)

        stmt = (
                select(AsignacionServicio)
                .where(AsignacionServicio.empleado_id == empleado.id)
                .where(AsignacionServicio.empresa_id == empresa_id)
                .order_by(AsignacionServicio.fecha_asignacion.desc())
        )
        rows = db.execute(stmt).scalars().all()

        servicio_ids = {str(asignacion.servicio_id) for asignacion in rows if asignacion.servicio_id}
        servicio_nombres: dict[str, str] = {}
        if servicio_ids:
            servicios = db.execute(
                select(Servicio.id_servicio, Servicio.nombre).where(
                    Servicio.empresa_id == empresa_id,
                    Servicio.id_servicio.in_(servicio_ids),
                )
            ).all()
            servicio_nombres = {str(servicio_id): nombre for servicio_id, nombre in servicios}

        result: list[MiAsignacionOut] = []
        for asignacion in rows:
            incidente = asignacion.incidente
            result.append(
                MiAsignacionOut(
                    incidente_id=str(asignacion.incidente_id),
                    incidente_tipo=incidente.tipo if incidente else None,
                    incidente_descripcion=incidente.descripcion if incidente else None,
                    incidente_estado=incidente.estado if incidente else None,
                    incidente_latitud=float(incidente.latitud) if incidente and incidente.latitud is not None else None,
                    incidente_longitud=float(incidente.longitud) if incidente and incidente.longitud is not None else None,
                    fecha_asignacion=asignacion.fecha_asignacion.isoformat(),
                    estado_tarea=asignacion.estado_tarea,
                    servicio_id=asignacion.servicio_id,
                    servicio_nombre=servicio_nombres.get(str(asignacion.servicio_id)),
                )
            )

        return result


@router.get("/{empleado_id}/", response_model=EmpleadoOut)
def empleados_retrieve(
    empleado_id: str,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EmpleadoOut:
    empleado = resolve_employee(db, user)
    empresa_id = resolve_tenant_empresa_id(user, empleado)
    row = get_empleado_or_404(db, empleado_id, empresa_id)
    return _serialize_empleado(row, get_base_url(request))


@router.post("/", response_model=EmpleadoOut, status_code=status.HTTP_201_CREATED)
async def empleados_create(
    request: Request,
    user: User = Depends(require_permission("manage_empleado")),
    db: Session = Depends(get_db),
) -> EmpleadoOut:
    empresa_id = _resolve_target_empresa_id(db, user)

    mode = _parse_payload(request)

    foto_path = None
    if mode == "form":
        form_data = await request.form()
        payload = _resolve_create_payload_from_form(form_data)
        maybe_file = form_data.get("foto_perfil")
        if isinstance(maybe_file, UploadFile) and maybe_file.filename:
            foto_path = save_profile_image(maybe_file, empresa_id)
    else:
        payload = EmpleadoCreate(**(await request.json()))

    row = create_empleado(db, payload, empresa_id=empresa_id, foto_path=foto_path)
    return _serialize_empleado(row, get_base_url(request))


@router.patch("/{empleado_id}/", response_model=EmpleadoOut)
@router.put("/{empleado_id}/", response_model=EmpleadoOut)
async def empleados_update(
    empleado_id: str,
    request: Request,
    user: User = Depends(require_permission("manage_empleado")),
    db: Session = Depends(get_db),
) -> EmpleadoOut:
    empleado_actor = resolve_employee(db, user)
    empresa_id = resolve_tenant_empresa_id(user, empleado_actor)
    target = get_empleado_or_404(db, empleado_id, empresa_id)

    mode = _parse_payload(request)

    foto_path = None
    if mode == "form":
        form_data = await request.form()
        payload = _resolve_update_payload_from_form(form_data)
        maybe_file = form_data.get("foto_perfil")
        if isinstance(maybe_file, UploadFile) and maybe_file.filename:
            foto_path = save_profile_image(maybe_file, target.empresa_id)
    else:
        payload = EmpleadoUpdate(**(await request.json()))

    row = update_empleado(db, target, payload, foto_path=foto_path)
    return _serialize_empleado(row, get_base_url(request))


@router.delete("/{empleado_id}/", status_code=status.HTTP_204_NO_CONTENT)
def empleados_delete(
    empleado_id: str,
    user: User = Depends(require_permission("manage_empleado")),
    db: Session = Depends(get_db),
) -> Response:
    empleado_actor = resolve_employee(db, user)
    empresa_id = resolve_tenant_empresa_id(user, empleado_actor)
    target = get_empleado_or_404(db, empleado_id, empresa_id)
    delete_empleado(db, target)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
