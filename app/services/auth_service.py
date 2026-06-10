from datetime import timedelta

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.config import get_settings
from app.core.security import create_token, decode_token, verify_password
from app.db.models import Cliente, Empleado, Rol, User

settings = get_settings()


def _employee_with_relations(db: Session, user_id: int) -> Empleado | None:
    stmt = (
        select(Empleado)
        .where(Empleado.usuario_id == user_id)
        .options(joinedload(Empleado.empresa), joinedload(Empleado.roles).joinedload(Rol.permisos))
    )
    return db.execute(stmt).scalars().first()


def build_user_claims(db: Session, user: User) -> dict:
    empleado = _employee_with_relations(db, user.id)
    cliente = db.execute(select(Cliente).where(Cliente.usuario_id == user.id)).scalars().first()

    if empleado:
        full_name = (empleado.nombre_completo or user.first_name or user.username).strip()
        role_names = [rol.nombre for rol in empleado.roles]
        # Consider empleado roles as source of truth for admin status (fall back to user.is_staff)
        admin_aliases = {"admin", "administrador"}
        role_name_set = {(r or "").strip().lower() for r in role_names}
        is_admin_by_role = any(alias in role_name_set for alias in admin_aliases)
        is_admin = bool(user.is_staff) or is_admin_by_role
        role_value = "admin" if is_admin else "empleado"
        return {
            "username": user.username,
            "email": user.email,
            "nombre_completo": full_name or user.username,
            "empresa_id": empleado.empresa_id,
            "empresa_nombre": empleado.empresa.nombre if empleado.empresa else None,
            "roles": role_names,
            "role": role_value,
            "is_admin": is_admin,
            "empleado_id": empleado.id,
            "cliente_id": None,
            "foto_perfil": empleado.foto_perfil,
        }

    if cliente:
        full_name = (cliente.nombre or user.first_name or user.username).strip()
        return {
            "username": user.username,
            "email": user.email,
            "nombre_completo": full_name or user.username,
            "empresa_id": None,
            "empresa_nombre": None,
            "roles": ["cliente"],
            "role": "cliente",
            "is_admin": False,
            "empleado_id": None,
            "cliente_id": cliente.id,
            "foto_perfil": None,
        }

    return {
        "username": user.username,
        "email": user.email,
        "nombre_completo": user.username,
        "empresa_id": None,
        "empresa_nombre": None,
        "roles": [],
        "role": "usuario",
        "is_admin": bool(user.is_staff),
        "empleado_id": None,
        "cliente_id": None,
        "foto_perfil": None,
    }


def authenticate_user(db: Session, username: str, password: str) -> User:
    stmt = select(User).where(User.username == username)
    user = db.execute(stmt).scalars().first()

    if not user or not user.is_active or not verify_password(password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No active account found with the given credentials",
        )

    return user


def create_token_pair(db: Session, user: User) -> dict[str, str]:
    claims = build_user_claims(db, user)
    access = create_token(
        subject=user.id,
        token_type="access",
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
        extra=claims,
    )
    refresh = create_token(
        subject=user.id,
        token_type="refresh",
        expires_delta=timedelta(days=settings.refresh_token_expire_days),
    )
    return {"access": access, "refresh": refresh}


def refresh_access_token(db: Session, refresh_token: str) -> str:
    try:
        payload = decode_token(refresh_token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido") from exc

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")

    subject = payload.get("sub")
    if not subject:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")

    user = db.get(User, int(subject))
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario inválido")

    claims = build_user_claims(db, user)
    return create_token(
        subject=user.id,
        token_type="access",
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
        extra=claims,
    )
