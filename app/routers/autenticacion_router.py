from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Cliente, User
from app.db.session import get_db
from app.deps.auth import get_current_user
from app.schemas.auth import AccessTokenResponse, LoginRequest, RefreshRequest, TokenResponse, FcmTokenUpdate
from app.schemas.empleado import EmpleadoInvitationActivateRequest
from app.schemas.cliente import ClienteCreate
from app.schemas.register import RegisterAdminRequest, RegisterCompanyRequest, RegisterCompanyResponse, RegisterEmpresaRequest

from app.services.auth_service import authenticate_user, create_token_pair, refresh_access_token
from app.services.permission_service import get_user_permissions, resolve_employee
from app.services.user_management import activate_empleado_invitation, register_admin_step, register_empresa_step, register_empresa_with_admin
from app.services.cliente_service import create_cliente, get_cliente_for_user
from app.services.permission_service import resolve_employee

router = APIRouter(tags=["auth"])


@router.post("/token/", response_model=TokenResponse)
def token_obtain(payload: LoginRequest, db: Session = Depends(get_db)) -> dict[str, str]:
    user = authenticate_user(db, payload.username, payload.password)
    return create_token_pair(db, user)


@router.post("/login", response_model=TokenResponse)
def login_legacy(payload: LoginRequest, db: Session = Depends(get_db)) -> dict[str, str]:
    user = authenticate_user(db, payload.username, payload.password)
    return create_token_pair(db, user)


@router.post("/token/refresh/", response_model=AccessTokenResponse)
def token_refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> dict[str, str]:
    access = refresh_access_token(db, payload.refresh)
    return {"access": access}


@router.post("/register/", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterEmpresaRequest, db: Session = Depends(get_db)) -> dict[str, str]:
    user = register_empresa_with_admin(db, payload)
    return create_token_pair(db, user)


@router.post("/register/company/", response_model=RegisterCompanyResponse, status_code=status.HTTP_201_CREATED)
def register_company(payload: RegisterCompanyRequest, db: Session = Depends(get_db)) -> RegisterCompanyResponse:
    result = register_empresa_step(db, payload)
    return RegisterCompanyResponse(**result)


@router.post("/register/admin/", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register_admin(payload: RegisterAdminRequest, db: Session = Depends(get_db)) -> dict[str, str]:
    user = register_admin_step(db, payload)
    return create_token_pair(db, user)


@router.post("/register/client/", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register_client(payload: ClienteCreate, db: Session = Depends(get_db)) -> dict[str, str]:
    cliente = create_cliente(db, payload)
    user = db.get(User, cliente.usuario_id) if cliente.usuario_id else None
    if not user:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="No se pudo crear el usuario del cliente")
    return create_token_pair(db, user)


@router.post("/employee-invitations/activate/", response_model=TokenResponse)
def activate_employee_invitation(payload: EmpleadoInvitationActivateRequest, db: Session = Depends(get_db)) -> dict[str, str]:
    user = activate_empleado_invitation(db, payload)
    return create_token_pair(db, user)


@router.get("/me")
def me_legacy(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    empleado = resolve_employee(db, user)
    cliente = get_cliente_for_user(db, user.id)
    role_names = {(role.nombre or "").strip().lower() for role in (empleado.roles if empleado else [])}
    is_admin_role = "admin" in role_names or "administrador" in role_names

    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "role": "admin" if user.is_staff else ("cliente" if cliente else ("empleado" if empleado else "usuario")),
        "es_admin": bool(user.is_staff) or is_admin_role,
        "empresa_id": empleado.empresa_id if empleado else None,
        "cliente_id": cliente.id if cliente else None,
        "is_active": bool(user.is_active),
        "created_at": user.date_joined.isoformat() if user.date_joined else None,
    }


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout_legacy() -> Response:
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/my-permissions/")
def my_permissions(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[str]:
    return sorted(list(get_user_permissions(db, user)))


@router.patch("/fcm-token")
def update_fcm_token(payload: FcmTokenUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    """Actualizar FCM token para el usuario autenticado (empleado o cliente)."""
    empleado = resolve_employee(db, user)
    if empleado:
        empleado.fcm_token = payload.fcm_token
        user.fcm_token = payload.fcm_token
        db.commit()
        return {"message": "FCM token actualizado"}

    cliente = get_cliente_for_user(db, user.id)
    if cliente:
        cliente.fcm_token = payload.fcm_token
        user.fcm_token = payload.fcm_token
        db.commit()
        return {"message": "FCM token actualizado"}

    if user.is_staff:
        user.fcm_token = payload.fcm_token
        db.commit()
        return {"message": "FCM token actualizado"}

    # No asociado a cliente ni empleado ni staff
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Usuario no asociado a cliente ni empleado")
