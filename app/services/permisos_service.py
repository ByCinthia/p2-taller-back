from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.db.models import Empleado, Rol, Suscripcion, User

ADMIN_ROLE_ALIASES = {"admin", "administrador"}
ADMIN_BASE_PERMISSIONS = {
    "manage_cargo",
    "manage_clientes",
    "manage_incidentes",
    "manage_empleado",
    "manage_rol",
    "manage_permiso",
    "view_cargo",
    "view_clientes",
    "view_incidentes",
    "view_empleado",
    "view_rol",
    "view_permiso",
}


def resolve_employee(db: Session, user: User) -> Empleado | None:
    stmt = (
        select(Empleado)
        .where(Empleado.usuario_id == user.id)
        .options(joinedload(Empleado.roles).joinedload(Rol.permisos), joinedload(Empleado.empresa))
    )
    return db.execute(stmt).scalars().first()


def get_user_permissions(db: Session, user: User) -> set[str]:
    permissions: set[str] = set()

    empleado = resolve_employee(db, user)
    if empleado:
        for role in empleado.roles:
            if (role.nombre or "").strip().lower() in ADMIN_ROLE_ALIASES:
                permissions.update(ADMIN_BASE_PERMISSIONS)
            for perm in role.permisos:
                permissions.add(perm.nombre)

        suscripcion = db.execute(select(Suscripcion).where(Suscripcion.empresa_id == empleado.empresa_id)).scalars().first()
        if suscripcion:
            if suscripcion.plan in {"profesional", "empresarial"}:
                permissions.add("view_custom_reports")
            if suscripcion.plan == "empresarial":
                permissions.add("view_advanced_reports")
                permissions.add("has_api_access")

    if user.is_staff:
        permissions.add("is_superuser")

    return permissions


def has_named_permission(db: Session, user: User, permission_name: str) -> bool:
    if user.is_staff:
        return True
    return permission_name in get_user_permissions(db, user)
