"""Tenant context dependency for multi-tenant isolation.

Provides reusable FastAPI dependencies that resolve the current user's
empresa_id (tenant) from the JWT token.  This avoids having every endpoint
manually call ``resolve_employee`` + ``resolve_tenant_empresa_id``.
"""
from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.models import Empleado, User
from app.db.session import get_db
from app.deps.auth import get_current_user
from app.services.permission_service import resolve_employee


@dataclass
class TenantContext:
    """Holds the resolved tenant information for the current request."""
    user: User
    empleado: Empleado | None
    empresa_id: str | None


def get_tenant(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TenantContext:
    """Resolve tenant context.

    * Staff users that also have an Empleado record are scoped to that empresa.
    * Staff users without an Empleado get ``empresa_id=None`` (global access).
    * Non-staff users **must** have an Empleado record or the request fails.
    """
    empleado = resolve_employee(db, user)

    if user.is_staff:
        return TenantContext(
            user=user,
            empleado=empleado,
            empresa_id=empleado.empresa_id if empleado else None,
        )

    if not empleado:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario no está asociado a un taller",
        )

    return TenantContext(
        user=user,
        empleado=empleado,
        empresa_id=empleado.empresa_id,
    )


def require_tenant(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TenantContext:
    """Like ``get_tenant`` but **always** requires an empresa association.

    Use this for endpoints that only make sense in the context of a specific
    taller (e.g. managing their own services, employees, etc.).
    """
    empleado = resolve_employee(db, user)

    if not empleado:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario no está asociado a un taller",
        )

    return TenantContext(
        user=user,
        empleado=empleado,
        empresa_id=empleado.empresa_id,
    )
