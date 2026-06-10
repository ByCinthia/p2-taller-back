from collections.abc import Callable

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.db.models import Empleado, User
from app.db.session import get_db
from app.services.permission_service import has_named_permission, resolve_employee

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication credentials were not provided")

    token = credentials.credentials
    try:
        payload = decode_token(token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    subject = payload.get("sub")
    if not subject:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user = db.get(User, int(subject))
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User inactive or not found")

    return user


def get_current_employee(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Empleado:
    empleado = resolve_employee(db, user)
    if not empleado:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El usuario no está asociado a un empleado")
    return empleado


def require_permission(permission_name: str) -> Callable:
    def _dependency(
        user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        if not has_named_permission(db, user, permission_name):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f'Permiso "{permission_name}" requerido.',
            )
        return user

    return _dependency


def resolve_tenant_empresa_id(user: User, empleado: Empleado | None) -> str | None:
    # Staff users that are also attached to an employee record should stay
    # scoped to their company. Only truly global staff fall back to None.
    if user.is_staff and empleado:
        return empleado.empresa_id
    if user.is_staff:
        return None
    if not empleado:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El usuario no está asociado a un taller")
    return empleado.empresa_id


def get_base_url(request: Request) -> str:
    return str(request.base_url).rstrip("/")
