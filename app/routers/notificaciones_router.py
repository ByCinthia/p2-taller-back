from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Notificacion, User
from app.db.session import get_db
from app.deps.auth import get_current_user
from app.schemas.notificacion import NotificacionListOut, NotificacionOut

router = APIRouter(prefix="/notificaciones", tags=["notificaciones"])


def _serialize_notification(notification: Notificacion) -> NotificacionOut:
    data: dict = {}
    if notification.data_json:
        try:
            data = json.loads(notification.data_json)
        except Exception:
            data = {}

    return NotificacionOut(
        id=notification.id,
        titulo=notification.titulo,
        mensaje=notification.mensaje,
        tipo=notification.tipo,
        data=data,
        leida=bool(notification.leida),
        leida_en=notification.leida_en,
        creada_en=notification.creada_en,
    )


@router.get("/me/", response_model=NotificacionListOut)
def my_notifications(
    limit: int = Query(default=50, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NotificacionListOut:
    stmt = (
        select(Notificacion)
        .where(Notificacion.user_id == user.id)
        .order_by(Notificacion.creada_en.desc())
        .limit(limit)
    )
    notifications = db.execute(stmt).scalars().all()
    return NotificacionListOut(
        items=[_serialize_notification(notification) for notification in notifications],
        total=len(notifications),
    )


@router.patch("/{notification_id}/leer", response_model=NotificacionOut)
def mark_notification_as_read(
    notification_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NotificacionOut:
    notification = db.get(Notificacion, notification_id)
    if not notification or notification.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notificación no encontrada")

    if not notification.leida:
        notification.leida = True
        notification.leida_en = datetime.now(timezone.utc)
        db.add(notification)
        db.commit()
        db.refresh(notification)

    return _serialize_notification(notification)
