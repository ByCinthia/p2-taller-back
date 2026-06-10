from __future__ import annotations

import re
import secrets
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.config import get_settings
from app.core.security import create_token, decode_token
from app.core.security import hash_password
from app.db.models import Cargo, Empleado, Empresa, Permiso, Rol, Servicio, Suscripcion, User
from app.schemas.empleado import EmpleadoCreate, EmpleadoInvitationActivateRequest, EmpleadoUpdate
from app.schemas.register import RegisterAdminRequest, RegisterCompanyRequest, RegisterEmpresaRequest
from app.services.email_service import send_employee_invitation_email

PLAN_LIMITS = {
    "basico": {"usuarios": 15, "activos": 100},
    "profesional": {"usuarios": 40, "activos": 350},
    "empresarial": {"usuarios": 9999, "activos": 99999},
}

DEFAULT_PERMISSIONS: list[tuple[str, str]] = [
    ("manage_cargo", "Gestionar cargos (crear, editar y eliminar)."),
    ("manage_clientes", "Gestionar clientes y vehiculos (crear, editar y eliminar)."),
    ("manage_empleado", "Gestionar empleados (crear, editar y eliminar)."),
    ("manage_rol", "Gestionar roles (crear, editar y eliminar)."),
    ("manage_permiso", "Gestionar permisos del sistema."),
    ("manage_servicio", "Gestionar servicios (crear, editar y eliminar)."),
    ("view_cargo", "Ver cargos."),
    ("view_clientes", "Ver clientes y vehiculos."),
    ("view_empleado", "Ver empleados."),
    ("view_rol", "Ver roles."),
    ("view_permiso", "Ver permisos."),
    ("view_servicio", "Ver servicios."),
]

REGISTER_ADMIN_TOKEN_MINUTES = 30
INVITATION_TOKEN_TYPE = "employee_activation"
settings = get_settings()


# -----------------------------
# Shared mapping helpers
# -----------------------------

def _serialize_permiso(permiso: Permiso) -> dict:
    return {
        "id": permiso.id,
        "nombre": permiso.nombre,
        "descripcion": permiso.descripcion,
    }


def _serialize_role(role: Rol) -> dict:
    return {
        "id": role.id,
        "empresa": role.empresa_id,
        "nombre": role.nombre,
        "permisos": [_serialize_permiso(p) for p in role.permisos],
    }


def _serialize_user(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "is_active": bool(user.is_active),
    }


def _serialize_empleado(empleado: Empleado, base_url: str) -> dict:
    foto = empleado.foto_perfil
    if foto:
        foto = f"{base_url}/media/{foto}".replace("//media", "/media")

    return {
        "id": empleado.id,
        "usuario": _serialize_user(empleado.usuario),
        "ci": empleado.ci,
        "nombre_completo": empleado.nombre_completo,
        "direccion": empleado.direccion,
        "telefono": empleado.telefono,
        "sueldo": empleado.sueldo,
        "cargo": empleado.cargo_id,
        "empresa": empleado.empresa_id,
        "foto_perfil": foto,
        "roles": [r.id for r in empleado.roles],
        "roles_asignados": [_serialize_role(r) for r in empleado.roles],
        "cargo_nombre": empleado.cargo.nombre if empleado.cargo else None,
    }


def _serialize_cargo(cargo: Cargo) -> dict:
    return {
        "id": cargo.id,
        "empresa": cargo.empresa_id,
        "nombre": cargo.nombre,
        "descripcion": cargo.descripcion,
    }


def _serialize_servicio(servicio: Servicio) -> dict:
    return {
        "id_servicio": servicio.id_servicio,
        "nombre": servicio.nombre,
        "descripcion": servicio.descripcion,
        "activo": bool(servicio.activo),
    }


# -----------------------------
# Permissions CRUD
# -----------------------------

def list_permisos(db: Session) -> list[Permiso]:
    return db.execute(select(Permiso).order_by(Permiso.nombre)).scalars().all()


def ensure_default_permissions(db: Session) -> list[Permiso]:
    existing = {perm.nombre: perm for perm in list_permisos(db)}

    for name, description in DEFAULT_PERMISSIONS:
        if name in existing:
            continue
        permiso = Permiso(id=str(uuid.uuid4()), nombre=name, descripcion=description)
        db.add(permiso)

    db.flush()
    return list_permisos(db)


def get_permiso_or_404(db: Session, permiso_id: str) -> Permiso:
    permiso = db.get(Permiso, permiso_id)
    if not permiso:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permiso no encontrado")
    return permiso


def create_permiso(db: Session, nombre: str, descripcion: str) -> Permiso:
    exists = db.execute(select(Permiso).where(func.lower(Permiso.nombre) == nombre.lower())).scalars().first()
    if exists:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ya existe un permiso con ese nombre")

    permiso = Permiso(id=str(uuid.uuid4()), nombre=nombre, descripcion=descripcion)
    db.add(permiso)
    db.commit()
    db.refresh(permiso)
    return permiso


def update_permiso(db: Session, permiso: Permiso, nombre: str | None, descripcion: str | None) -> Permiso:
    if nombre and nombre.lower() != permiso.nombre.lower():
        exists = db.execute(select(Permiso).where(func.lower(Permiso.nombre) == nombre.lower())).scalars().first()
        if exists:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ya existe un permiso con ese nombre")
        permiso.nombre = nombre

    if descripcion is not None:
        permiso.descripcion = descripcion

    db.add(permiso)
    db.commit()
    db.refresh(permiso)
    return permiso


def delete_permiso(db: Session, permiso: Permiso) -> None:
    db.delete(permiso)
    db.commit()


# -----------------------------
# Cargos CRUD
# -----------------------------

def list_cargos(db: Session, empresa_id: str | None) -> list[Cargo]:
    stmt = select(Cargo)
    if empresa_id:
        stmt = stmt.where(Cargo.empresa_id == empresa_id)
    return db.execute(stmt.order_by(Cargo.nombre)).scalars().all()


def get_cargo_or_404(db: Session, cargo_id: str, empresa_id: str | None) -> Cargo:
    cargo = db.get(Cargo, cargo_id)
    if not cargo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cargo no encontrado")
    if empresa_id and cargo.empresa_id != empresa_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cargo no encontrado")
    return cargo


def create_cargo(db: Session, empresa_id: str, nombre: str, descripcion: str | None) -> Cargo:
    exists_stmt = select(Cargo).where(Cargo.empresa_id == empresa_id, func.lower(Cargo.nombre) == nombre.lower())
    if db.execute(exists_stmt).scalars().first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ya existe un cargo con ese nombre en la empresa")

    cargo = Cargo(id=str(uuid.uuid4()), empresa_id=empresa_id, nombre=nombre, descripcion=descripcion)
    db.add(cargo)
    db.commit()
    db.refresh(cargo)
    return cargo


def update_cargo(db: Session, cargo: Cargo, nombre: str | None, descripcion: str | None) -> Cargo:
    if nombre and nombre.lower() != cargo.nombre.lower():
        exists_stmt = select(Cargo).where(
            Cargo.empresa_id == cargo.empresa_id,
            func.lower(Cargo.nombre) == nombre.lower(),
            Cargo.id != cargo.id,
        )
        if db.execute(exists_stmt).scalars().first():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ya existe un cargo con ese nombre en la empresa")
        cargo.nombre = nombre

    if descripcion is not None:
        cargo.descripcion = descripcion

    db.add(cargo)
    db.commit()
    db.refresh(cargo)
    return cargo


def delete_cargo(db: Session, cargo: Cargo) -> None:
    db.delete(cargo)
    db.commit()


# -----------------------------
# Servicios CRUD
# -----------------------------

def list_servicios(db: Session, empresa_id: str | None) -> list[Servicio]:
    stmt = select(Servicio)
    if empresa_id:
        stmt = stmt.where(Servicio.empresa_id == empresa_id)
    return db.execute(stmt.order_by(Servicio.nombre)).scalars().all()


def get_servicio_or_404(db: Session, servicio_id: str, empresa_id: str | None) -> Servicio:
    servicio = db.get(Servicio, servicio_id)
    if not servicio:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Servicio no encontrado")
    if empresa_id and servicio.empresa_id != empresa_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Servicio no encontrado")
    return servicio


def create_servicio(db: Session, empresa_id: str, nombre: str, descripcion: str | None, activo: bool) -> Servicio:
    exists_stmt = select(Servicio).where(Servicio.empresa_id == empresa_id, func.lower(Servicio.nombre) == nombre.lower())
    if db.execute(exists_stmt).scalars().first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ya existe un servicio con ese nombre en la empresa")

    servicio = Servicio(
        id_servicio=str(uuid.uuid4()),
        empresa_id=empresa_id,
        nombre=nombre,
        descripcion=descripcion,
        activo=bool(activo),
    )
    db.add(servicio)
    db.commit()
    db.refresh(servicio)
    return servicio


def update_servicio(db: Session, servicio: Servicio, nombre: str | None, descripcion: str | None, activo: bool | None) -> Servicio:
    if nombre and nombre.lower() != servicio.nombre.lower():
        exists_stmt = select(Servicio).where(
            Servicio.empresa_id == servicio.empresa_id,
            func.lower(Servicio.nombre) == nombre.lower(),
            Servicio.id_servicio != servicio.id_servicio,
        )
        if db.execute(exists_stmt).scalars().first():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ya existe un servicio con ese nombre en la empresa")
        servicio.nombre = nombre

    if descripcion is not None:
        servicio.descripcion = descripcion

    if activo is not None:
        servicio.activo = bool(activo)

    db.add(servicio)
    db.commit()
    db.refresh(servicio)
    return servicio


def delete_servicio(db: Session, servicio: Servicio) -> None:
    db.delete(servicio)
    db.commit()


# -----------------------------
# Roles CRUD
# -----------------------------

def _resolve_role_permissions(db: Session, permission_ids: list[str]) -> list[Permiso]:
    if not permission_ids:
        return []

    permisos = db.execute(select(Permiso).where(Permiso.id.in_(permission_ids))).scalars().all()
    found = {p.id for p in permisos}
    missing = [pid for pid in permission_ids if pid not in found]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Permisos no encontrados: {', '.join(missing)}",
        )
    return permisos


def list_roles(db: Session, empresa_id: str | None) -> list[Rol]:
    stmt = select(Rol).options(joinedload(Rol.permisos))
    if empresa_id:
        stmt = stmt.where(Rol.empresa_id == empresa_id)
    return db.execute(stmt.order_by(Rol.nombre)).unique().scalars().all()


def get_role_or_404(db: Session, role_id: str, empresa_id: str | None) -> Rol:
    stmt = select(Rol).where(Rol.id == role_id).options(joinedload(Rol.permisos))
    role = db.execute(stmt).unique().scalars().first()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rol no encontrado")
    if empresa_id and role.empresa_id != empresa_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rol no encontrado")
    return role


def create_role(db: Session, empresa_id: str, nombre: str, permission_ids: list[str]) -> Rol:
    exists_stmt = select(Rol).where(Rol.empresa_id == empresa_id, func.lower(Rol.nombre) == nombre.lower())
    if db.execute(exists_stmt).scalars().first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ya existe un rol con ese nombre en la empresa")

    role = Rol(id=str(uuid.uuid4()), empresa_id=empresa_id, nombre=nombre)
    role.permisos = _resolve_role_permissions(db, permission_ids)

    db.add(role)
    db.commit()
    db.refresh(role)
    return db.execute(select(Rol).where(Rol.id == role.id).options(joinedload(Rol.permisos))).unique().scalars().one()


def update_role(db: Session, role: Rol, nombre: str | None, permission_ids: list[str] | None) -> Rol:
    if nombre and nombre.lower() != role.nombre.lower():
        exists_stmt = select(Rol).where(
            Rol.empresa_id == role.empresa_id,
            func.lower(Rol.nombre) == nombre.lower(),
            Rol.id != role.id,
        )
        if db.execute(exists_stmt).scalars().first():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ya existe un rol con ese nombre en la empresa")
        role.nombre = nombre

    if permission_ids is not None:
        role.permisos = _resolve_role_permissions(db, permission_ids)

    db.add(role)
    db.commit()
    db.refresh(role)
    return db.execute(select(Rol).where(Rol.id == role.id).options(joinedload(Rol.permisos))).unique().scalars().one()


def delete_role(db: Session, role: Rol) -> None:
    db.delete(role)
    db.commit()


# -----------------------------
# Empleados CRUD
# -----------------------------

def _validate_optional_fk(db: Session, model: type[Cargo], model_id: str | None, name: str) -> str | None:
    if not model_id or (isinstance(model_id, str) and model_id.strip() == ""):
        return None
    row = db.get(model, model_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{name} no encontrado")
    return model_id


def _validate_role_ids(db: Session, role_ids: list[str], empresa_id: str) -> list[Rol]:
    if not role_ids:
        return []

    roles = db.execute(select(Rol).where(Rol.id.in_(role_ids), Rol.empresa_id == empresa_id)).scalars().all()
    found = {r.id for r in roles}
    missing = [rid for rid in role_ids if rid not in found]
    if missing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Roles no válidos para la empresa: {', '.join(missing)}")
    return roles


def _validate_subscription_user_limit(db: Session, empresa_id: str) -> None:
    suscripcion = db.execute(select(Suscripcion).where(Suscripcion.empresa_id == empresa_id)).scalars().first()
    if not suscripcion:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Error: No se encontró una suscripción para tu taller.")

    if suscripcion.estado != "activa":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tu suscripción no está activa. No puedes añadir nuevos registros en el taller.",
        )

    current_count = db.execute(select(func.count(Empleado.id)).where(Empleado.empresa_id == empresa_id)).scalar_one()
    if current_count >= suscripcion.max_usuarios:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Has alcanzado el límite de {suscripcion.max_usuarios} empleados para tu plan "
                f"{suscripcion.plan}. Por favor, actualiza tu plan."
            ),
        )


def list_empleados(
    db: Session,
    empresa_id: str | None,
    exclude_user_id: int | None = None,
    exclude_admin_roles: bool = False,
) -> list[Empleado]:
    stmt = (
        select(Empleado)
        .options(
            joinedload(Empleado.usuario),
            joinedload(Empleado.cargo),
            joinedload(Empleado.roles).joinedload(Rol.permisos),
        )
        .order_by(Empleado.nombre_completo)
    )
    if empresa_id:
        stmt = stmt.where(Empleado.empresa_id == empresa_id)
    if exclude_user_id is not None:
        stmt = stmt.where(Empleado.usuario_id != exclude_user_id)
    rows = db.execute(stmt).unique().scalars().all()
    if not exclude_admin_roles:
        return rows

    admin_aliases = {"admin", "administrador"}
    return [
        row
        for row in rows
        if all((role.nombre or "").strip().lower() not in admin_aliases for role in row.roles)
    ]


def get_empleado_or_404(db: Session, empleado_id: str, empresa_id: str | None) -> Empleado:
    stmt = (
        select(Empleado)
        .where(Empleado.id == empleado_id)
        .options(
            joinedload(Empleado.usuario),
            joinedload(Empleado.cargo),
            joinedload(Empleado.roles).joinedload(Rol.permisos),
        )
    )
    empleado = db.execute(stmt).unique().scalars().first()
    if not empleado:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empleado no encontrado")
    if empresa_id and empleado.empresa_id != empresa_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empleado no encontrado")
    return empleado


def _generate_pending_username(base_email: str) -> str:
    local_part = base_email.split("@", 1)[0].strip().lower() if "@" in base_email else "empleado"
    slug = re.sub(r"[^a-z0-9]+", "_", local_part).strip("_")
    if not slug:
        slug = "empleado"
    return f"pending_{slug}_{secrets.token_hex(4)}"


def _build_employee_invitation_url(token: str) -> str:
    return f"{settings.frontend_base_url.rstrip('/')}/activate-invite?token={token}"


def _create_employee_invitation_token(user_id: int, empresa_id: str) -> str:
    return create_token(
        subject=user_id,
        token_type=INVITATION_TOKEN_TYPE,
        expires_delta=timedelta(hours=settings.invitation_token_expire_hours),
        extra={"empresa_id": empresa_id},
    )


def create_empleado(db: Session, payload: EmpleadoCreate, empresa_id: str, foto_path: str | None = None) -> Empleado:
    _validate_subscription_user_limit(db, empresa_id)

    exists_email = db.execute(select(User).where(func.lower(User.email) == payload.email.lower())).scalars().first()
    if exists_email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Este correo electrónico ya está en uso")

    role_rows = _validate_role_ids(db, payload.roles, empresa_id)
    cargo_id = _validate_optional_fk(db, Cargo, payload.cargo, "Cargo")

    pending_username = _generate_pending_username(payload.email)
    user = User(
        username=pending_username,
        password=hash_password(secrets.token_urlsafe(24)),
        first_name=payload.nombre_completo,
        last_name="",
        email=payload.email,
        is_staff=False,
        is_superuser=False,
        is_active=False,
        date_joined=datetime.now(timezone.utc),
    )
    db.add(user)
    db.flush()

    empleado = Empleado(
        id=str(uuid.uuid4()),
        usuario_id=user.id,
        empresa_id=empresa_id,
        ci=payload.ci,
        nombre_completo=payload.nombre_completo,
        direccion=payload.direccion,
        telefono=payload.telefono,
        sueldo=payload.sueldo or Decimal("0"),
        cargo_id=cargo_id,
        foto_perfil=foto_path,
    )
    empleado.roles = role_rows

    invitation_token = _create_employee_invitation_token(user.id, empresa_id)
    invitation_url = _build_employee_invitation_url(invitation_token)

    db.add(empleado)
    db.commit()

    try:
        send_employee_invitation_email(
            to_email=payload.email,
            employee_name=payload.nombre_completo,
            invitation_url=invitation_url,
        )
    except Exception:
        # Keep employee creation successful even when SMTP is unavailable.
        pass

    return get_empleado_or_404(db, empleado.id, empresa_id=None)


def activate_empleado_invitation(db: Session, payload: EmpleadoInvitationActivateRequest) -> User:
    try:
        token_payload = decode_token(payload.token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invitación inválida o expirada") from exc

    if token_payload.get("type") != INVITATION_TOKEN_TYPE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invitación inválida")

    subject = token_payload.get("sub")
    if not subject:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invitación inválida")

    user = db.get(User, int(subject))
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario invitado no encontrado")

    if user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La invitación ya fue utilizada")

    username_clean = payload.username.strip()
    if not username_clean:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El nombre de usuario es obligatorio")

    exists_username = db.execute(select(User).where(func.lower(User.username) == username_clean.lower(), User.id != user.id)).scalars().first()
    if exists_username:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Este nombre de usuario ya está en uso")

    user.username = username_clean
    user.password = hash_password(payload.password)
    user.is_active = True
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_empleado(db: Session, empleado: Empleado, payload: EmpleadoUpdate, foto_path: str | None = None) -> Empleado:
    user = empleado.usuario

    if payload.nombre_completo is not None:
        user.first_name = payload.nombre_completo
        user.last_name = ""
    if payload.email is not None:
        user.email = payload.email

    if payload.ci is not None:
        empleado.ci = payload.ci
    if payload.nombre_completo is not None:
        empleado.nombre_completo = payload.nombre_completo
    if payload.direccion is not None:
        empleado.direccion = payload.direccion
    if payload.telefono is not None:
        empleado.telefono = payload.telefono
    if payload.sueldo is not None:
        empleado.sueldo = payload.sueldo

    if payload.cargo is not None:
        empleado.cargo_id = _validate_optional_fk(db, Cargo, payload.cargo, "Cargo")

    if foto_path is not None:
        empleado.foto_perfil = foto_path

    if payload.roles is not None:
        empleado.roles = _validate_role_ids(db, payload.roles, empleado.empresa_id)

    db.add(user)
    db.add(empleado)
    db.commit()
    return get_empleado_or_404(db, empleado.id, empresa_id=None)


def delete_empleado(db: Session, empleado: Empleado) -> None:
    user = empleado.usuario
    db.delete(empleado)
    db.flush()
    if user:
        db.delete(user)
    db.commit()


# -----------------------------
# Register Empresa + Admin
# -----------------------------

def _validate_register_company_payload(db: Session, payload: RegisterCompanyRequest | RegisterEmpresaRequest) -> None:
    if db.execute(select(Empresa).where(func.lower(Empresa.nombre) == payload.empresa_nombre.lower())).scalars().first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ya existe un taller con este nombre.")

    if db.execute(select(Empresa).where(func.lower(Empresa.nit) == payload.empresa_nit.lower())).scalars().first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ya existe un taller con este NIT.")

    if payload.card_number is not None and not re.match(r"^\d{16}$", payload.card_number):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El número de tarjeta debe contener exactamente 16 dígitos.")

    if payload.card_expiry is not None and not re.match(r"^(0[1-9]|1[0-2])\/\d{2}$", payload.card_expiry):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La fecha de expiración debe tener el formato MM/AA.")

    if payload.card_cvc is not None and not re.match(r"^\d{3,4}$", payload.card_cvc):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El CVC debe contener 3 o 4 dígitos.")

    has_any_payment_field = any([payload.card_number, payload.card_expiry, payload.card_cvc])
    has_all_payment_fields = all([payload.card_number, payload.card_expiry, payload.card_cvc])
    if has_any_payment_field and not has_all_payment_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Si envías datos de pago, debes incluir card_number, card_expiry y card_cvc.",
        )

    if payload.plan not in PLAN_LIMITS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Plan '{payload.plan}' inválido seleccionado.")


def _validate_admin_identity_uniqueness(db: Session, username: str, email: str) -> None:
    if db.execute(select(User).where(func.lower(User.username) == username.lower())).scalars().first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Este nombre de usuario ya está en uso.")

    if db.execute(select(User).where(func.lower(User.email) == email.lower())).scalars().first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Este correo electrónico ya está en uso.")


def _validate_register_admin_payload(db: Session, payload: RegisterAdminRequest) -> Empresa:
    _validate_admin_identity_uniqueness(db, payload.admin_username, payload.admin_email)

    try:
        token_payload = decode_token(payload.registration_token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token de registro inválido o expirado.") from exc

    if token_payload.get("type") != "register_admin":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token de registro inválido.")

    empresa_id = token_payload.get("empresa_id") or token_payload.get("sub")
    if not empresa_id or not isinstance(empresa_id, str):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token de registro inválido.")

    empresa = db.get(Empresa, empresa_id)
    if not empresa:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empresa no encontrada para el registro.")

    existing_admin = db.execute(select(Empleado).where(Empleado.empresa_id == empresa.id)).scalars().first()
    if existing_admin:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La empresa ya cuenta con administrador inicial.")

    return empresa


def _ensure_empresa_admin_role(db: Session, empresa_id: str) -> Rol:
    admin_role = db.execute(select(Rol).where(Rol.empresa_id == empresa_id, Rol.nombre == "Admin")).scalars().first()
    if not admin_role:
        admin_role = Rol(id=str(uuid.uuid4()), empresa_id=empresa_id, nombre="Admin")
        db.add(admin_role)
        db.flush()

    all_perms = ensure_default_permissions(db)
    admin_role.permisos = all_perms
    db.add(admin_role)
    db.flush()
    return admin_role


def register_empresa_step(db: Session, payload: RegisterCompanyRequest) -> dict[str, str]:
    _validate_register_company_payload(db, payload)

    now = datetime.now(timezone.utc)
    empresa = Empresa(
        id=str(uuid.uuid4()),
        nombre=payload.empresa_nombre,
        nit=payload.empresa_nit,
        email=payload.empresa_email.strip() if payload.empresa_email else None,
        telefono=payload.empresa_telefono.strip() if payload.empresa_telefono else None,
        direccion=payload.empresa_direccion.strip() if payload.empresa_direccion else None,
        fecha_creacion=now,
    )
    db.add(empresa)
    db.flush()

    plan_limits = PLAN_LIMITS[payload.plan]
    suscripcion = Suscripcion(
        id=str(uuid.uuid4()),
        empresa_id=empresa.id,
        plan=payload.plan,
        estado="activa",
        fecha_inicio=date.today(),
        fecha_fin=date.today() + timedelta(days=30),
        max_usuarios=plan_limits["usuarios"],
        max_activos=plan_limits["activos"],
    )
    db.add(suscripcion)

    _ensure_empresa_admin_role(db, empresa.id)
    db.commit()

    registration_token = create_token(
        subject=empresa.id,
        token_type="register_admin",
        expires_delta=timedelta(minutes=REGISTER_ADMIN_TOKEN_MINUTES),
        extra={"empresa_id": empresa.id},
    )
    return {
        "empresa_id": empresa.id,
        "empresa_nombre": empresa.nombre,
        "registration_token": registration_token,
    }


def register_admin_step(db: Session, payload: RegisterAdminRequest) -> User:
    empresa = _validate_register_admin_payload(db, payload)

    now = datetime.now(timezone.utc)
    user = User(
        username=payload.admin_username,
        password=hash_password(payload.admin_password),
        first_name=payload.admin_first_name,
        last_name=payload.admin_apellido_p,
        email=payload.admin_email,
        is_staff=False,
        is_superuser=False,
        is_active=True,
        date_joined=now,
    )
    db.add(user)
    db.flush()

    empleado = Empleado(
        id=str(uuid.uuid4()),
        usuario_id=user.id,
        empresa_id=empresa.id,
        ci=payload.admin_ci,
        nombre_completo=f"{payload.admin_first_name} {payload.admin_apellido_p} {payload.admin_apellido_m}".strip(),
        sueldo=Decimal("0"),
    )
    admin_role = _ensure_empresa_admin_role(db, empresa.id)
    empleado.roles = [admin_role]

    db.add(empleado)
    db.commit()
    db.refresh(user)
    return user


def register_empresa_with_admin(db: Session, payload: RegisterEmpresaRequest) -> User:
    _validate_register_company_payload(db, payload)
    _validate_admin_identity_uniqueness(db, payload.admin_username, payload.admin_email)

    now = datetime.now(timezone.utc)
    empresa = Empresa(
        id=str(uuid.uuid4()),
        nombre=payload.empresa_nombre,
        nit=payload.empresa_nit,
        email=payload.empresa_email.strip() if payload.empresa_email else None,
        telefono=payload.empresa_telefono.strip() if payload.empresa_telefono else None,
        direccion=payload.empresa_direccion.strip() if payload.empresa_direccion else None,
        fecha_creacion=now,
    )
    db.add(empresa)
    db.flush()

    plan_limits = PLAN_LIMITS[payload.plan]
    suscripcion = Suscripcion(
        id=str(uuid.uuid4()),
        empresa_id=empresa.id,
        plan=payload.plan,
        estado="activa",
        fecha_inicio=date.today(),
        fecha_fin=date.today() + timedelta(days=30),
        max_usuarios=plan_limits["usuarios"],
        max_activos=plan_limits["activos"],
    )
    db.add(suscripcion)
    db.flush()

    user = User(
        username=payload.admin_username,
        password=hash_password(payload.admin_password),
        first_name=payload.admin_first_name,
        last_name=payload.admin_apellido_p,
        email=payload.admin_email,
        is_staff=False,
        is_superuser=False,
        is_active=True,
        date_joined=now,
    )
    db.add(user)
    db.flush()

    empleado = Empleado(
        id=str(uuid.uuid4()),
        usuario_id=user.id,
        empresa_id=empresa.id,
        ci=payload.admin_ci,
        nombre_completo=f"{payload.admin_first_name} {payload.admin_apellido_p} {payload.admin_apellido_m}".strip(),
        sueldo=Decimal("0"),
    )
    admin_role = _ensure_empresa_admin_role(db, empresa.id)
    empleado.roles = [admin_role]

    db.add(empleado)
    db.commit()
    db.refresh(user)
    return user


__all__ = [
    "create_permiso",
    "update_permiso",
    "delete_permiso",
    "get_permiso_or_404",
    "list_permisos",
    "create_role",
    "update_role",
    "delete_role",
    "get_role_or_404",
    "list_roles",
    "create_servicio",
    "update_servicio",
    "delete_servicio",
    "get_servicio_or_404",
    "list_servicios",
    "create_empleado",
    "update_empleado",
    "delete_empleado",
    "activate_empleado_invitation",
    "get_empleado_or_404",
    "list_empleados",
    "register_empresa_step",
    "register_admin_step",
    "register_empresa_with_admin",
    "_serialize_role",
    "_serialize_permiso",
    "_serialize_empleado",
    "_serialize_servicio",
]
