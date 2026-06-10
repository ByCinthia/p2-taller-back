import uuid
import random
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.models import Cliente, User, Vehiculo
from app.schemas.cliente import ClienteCreate, ClienteUpdate

# Simple in-memory store for SMS codes (demo only)
_sms_codes: dict[str, str] = {}


def list_clientes(db: Session) -> list[Cliente]:
    return db.execute(select(Cliente)).scalars().all()


def create_cliente(db: Session, payload: ClienteCreate) -> Cliente:
    exists_username = db.execute(select(User).where(func.lower(User.username) == payload.username.lower())).scalars().first()
    if exists_username:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El nombre de usuario del cliente ya está en uso")

    user = User(
        username=payload.username.strip(),
        password=hash_password(payload.password),
        first_name=payload.nombre,
        last_name="",
        email=str(payload.email) if payload.email else "",
        is_staff=False,
        is_superuser=False,
        is_active=True,
        date_joined=datetime.now(timezone.utc),
    )
    db.add(user)
    db.flush()

    obj = Cliente(
        id=str(uuid.uuid4()),
        usuario_id=user.id,
        nombre=payload.nombre,
        email=str(payload.email) if payload.email else None,
        telefono=payload.telefono,
        activo=bool(payload.activo),
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def get_cliente_or_404(db: Session, cliente_id: str) -> Cliente:
    obj = db.get(Cliente, cliente_id)
    if not obj:
        raise ValueError("Cliente no encontrado")
    return obj


def get_cliente_for_user(db: Session, user_id: int) -> Cliente | None:
    return db.execute(select(Cliente).where(Cliente.usuario_id == user_id)).scalars().first()


def get_cliente_for_user_or_404(db: Session, user_id: int) -> Cliente:
    cliente = get_cliente_for_user(db, user_id)
    if not cliente:
        raise ValueError("Cliente no encontrado")
    return cliente


def update_cliente(db: Session, cliente: Cliente, payload: ClienteUpdate) -> Cliente:
    user = db.get(User, cliente.usuario_id) if cliente.usuario_id else None

    if payload.nombre is not None:
        cliente.nombre = payload.nombre
        if user:
            user.first_name = payload.nombre
    if payload.username is not None:
        exists_username = db.execute(
            select(User).where(func.lower(User.username) == payload.username.lower())
        ).scalars().first()
        if exists_username and (not user or exists_username.id != user.id):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El nombre de usuario del cliente ya está en uso")
        if user:
            user.username = payload.username.strip()
    if payload.password is not None and payload.password.strip():
        if user:
            user.password = hash_password(payload.password)
    if payload.email is not None:
        cliente.email = str(payload.email)
        if user:
            user.email = str(payload.email)
    if payload.telefono is not None:
        cliente.telefono = payload.telefono
    if payload.activo is not None:
        cliente.activo = bool(payload.activo)
        if user:
            user.is_active = bool(payload.activo)

    if user:
        db.add(user)
    db.add(cliente)
    db.commit()
    db.refresh(cliente)
    return cliente


def send_verification_sms(db: Session, cliente_id: str) -> str:
    # generate a 6-digit code and "send" it. In production integrate with SMS provider.
    code = f"{random.randint(0, 999999):06d}"
    _sms_codes[cliente_id] = code
    return code


def verify_sms(db: Session, cliente_id: str, code: str) -> bool:
    expected = _sms_codes.get(cliente_id)
    if not expected:
        return False
    if expected == code:
        del _sms_codes[cliente_id]
        return True
    return False


def get_cliente_historial(db: Session, cliente_id: str) -> list[Vehiculo]:
    # For now, historial returns the list of vehicles associated to the cliente
    cliente = get_cliente_or_404(db, cliente_id)
    return cliente.vehiculos
