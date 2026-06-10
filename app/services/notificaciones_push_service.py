from __future__ import annotations

import json
import logging
import uuid
from typing import Any

import firebase_admin
from firebase_admin import credentials, messaging
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import Empleado, Incidente, Notificacion, User

logger = logging.getLogger(__name__)
APP_TITLE = "Auxilio Mecanico Web"


def _store_notification(
    db: Session,
    user_id: int,
    titulo: str,
    mensaje: str,
    tipo: str | None = None,
    data: dict[str, str] | None = None,
) -> None:
    try:
        notification = Notificacion(
            id=str(uuid.uuid4()),
            user_id=user_id,
            titulo=titulo,
            mensaje=mensaje,
            tipo=tipo,
            data_json=json.dumps(data or {}, ensure_ascii=False),
        )
        db.add(notification)
        db.commit()
        db.refresh(notification)

        # Retransmitir en tiempo real vía WebSocket
        try:
            import asyncio
            from app.services.websocket_manager import notification_ws_manager
            payload = {
                "id": notification.id,
                "titulo": titulo,
                "mensaje": mensaje,
                "tipo": tipo or "",
                "data": data or {},
                "leida": False,
                "creada_en": notification.creada_en.isoformat() if notification.creada_en else None,
            }
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(notification_ws_manager.send_to_user(str(user_id), payload))
        except Exception as ws_err:
            logger.error(f"Error enviando notificacion por WebSocket: {ws_err}")
    except Exception:
        logger.exception("Error guardando notificación para user_id=%s", user_id)



def _init_firebase():
    try:
        # Allow multiple calls without reinitializing
        if not firebase_admin._apps:
            settings = get_settings()
            cred_path = settings.FIREBASE_CREDENTIALS_PATH or settings.firebase_credentials_path
            # fallback: look for auxiliomecanico.json in repository root or current cwd
            if not cred_path:
                from pathlib import Path

                cwd = Path.cwd()
                candidate = cwd / "auxiliomecanico.json"
                if candidate.exists():
                    cred_path = str(candidate)
                else:
                    # also check package root (two levels up from this file)
                    pkg_root_candidate = Path(__file__).resolve().parents[2] / "auxiliomecanico.json"
                    if pkg_root_candidate.exists():
                        cred_path = str(pkg_root_candidate)

            if not cred_path:
                logger.warning("FIREBASE_CREDENTIALS_PATH not configured and auxiliomecanico.json not found; FCM disabled")
                return None
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
        return firebase_admin.get_app()
    except Exception as exc:
        logger.exception("Error initializing Firebase: %s", exc)
        return None


def send_push_notification(token: str, title: str, body: str, data: dict[str, str] | None = None) -> Any:
    app = _init_firebase()
    if not app:
        raise RuntimeError("Firebase not initialized")

    message = messaging.Message(
        notification=messaging.Notification(title=title, body=body),
        data=data or {},
        token=token,
    )
    try:
        res = messaging.send(message)
        logger.info("FCM sent: %s", res)
        return res
    except Exception:
        logger.exception("Error sending FCM to token=%s", token)
        raise


def _notify_staff_users(
    db: Session,
    titulo: str,
    descripcion: str,
    tipo_notificacion: str,
    data: dict[str, str],
    user_ids_sent: set[int] | None = None,
) -> set[int]:
    sent_ids = user_ids_sent or set()
    stmt_users = select(User).where(User.is_staff == True)
    staff_users = db.execute(stmt_users).scalars().all()

    for staff_user in staff_users:
        if staff_user.id in sent_ids:
            continue
        _store_notification(db, staff_user.id, titulo, descripcion, tipo_notificacion, data)
        if staff_user.fcm_token:
            try:
                send_push_notification(staff_user.fcm_token, APP_TITLE, descripcion, data)
            except Exception:
                logger.exception("Error notificando usuario staff %s", staff_user.id)
        sent_ids.add(staff_user.id)

    return sent_ids


def notify_new_incident(db: Session, incidente: Incidente) -> None:
    # notify all administrators (backend-decided) about a new incident
    try:
        # Admins are users with is_staff=True OR Empleado roles that include admin
        # Query Empleado rows that are linked to a User with is_staff True, and also any Empleado rows
        # whose roles include 'admin' (defensive). Additionally, some admins may not be Empleado rows,
        # so also query User table directly and try to resolve an Empleado/Cliente fcm_token.
        from app.db.models import User, Cliente

        titulo = "Nueva solicitud de auxilio"
        descripcion_corta = (incidente.tipo or "")
        if incidente.descripcion:
            descripcion_corta = f"{descripcion_corta} - {incidente.descripcion[:60]}" if descripcion_corta else incidente.descripcion[:60]

        data = {
            "incidente_id": incidente.id,
            "tipo": incidente.tipo or "",
            "estado": incidente.estado or "",
            "titulo": titulo,
        }

        # First: all admins that are Empleado (regardless of FCM token)
        stmt_emp = select(Empleado)
        empleados = db.execute(stmt_emp).scalars().all()
        admin_emps = [e for e in empleados if (e.usuario and getattr(e.usuario, "is_staff", False)) or any("admin" in (r.nombre or "").lower() for r in (e.roles or []))]

        user_ids_sent = set()
        for emp in admin_emps:
            if not emp.usuario_id:
                continue
            if emp.usuario_id not in user_ids_sent:
                _store_notification(db, emp.usuario_id, titulo, descripcion_corta, "incident_created", data)
                user_ids_sent.add(emp.usuario_id)
            if not emp.fcm_token:
                continue
            try:
                send_push_notification(emp.fcm_token, APP_TITLE, descripcion_corta, data)
            except Exception:
                logger.exception("Error notificando a empleado admin %s", emp.id)

        # Second: any User rows with is_staff True that weren't covered above
        stmt_users = select(User).where(User.is_staff == True)
        users = db.execute(stmt_users).scalars().all()
        for user in users:
            # try to find an Empleado or Cliente associated
            try:
                emp = db.execute(select(Empleado).where(Empleado.usuario_id == user.id)).scalars().first()
                if emp:
                    if emp.usuario_id not in user_ids_sent:
                        _store_notification(db, emp.usuario_id, titulo, descripcion_corta, "incident_created", data)
                        user_ids_sent.add(emp.usuario_id)
                    if emp.fcm_token:
                        send_push_notification(emp.fcm_token, APP_TITLE, descripcion_corta, data)
                    continue

                cli = db.execute(select(Cliente).where(Cliente.usuario_id == user.id)).scalars().first()
                if cli:
                    if cli.usuario_id and cli.usuario_id not in user_ids_sent:
                        _store_notification(db, cli.usuario_id, titulo, descripcion_corta, "incident_created", data)
                        user_ids_sent.add(cli.usuario_id)
                    if cli.fcm_token:
                        send_push_notification(cli.fcm_token, APP_TITLE, descripcion_corta, data)
                    continue

                if user.is_staff and user.fcm_token:
                    if user.id not in user_ids_sent:
                        _store_notification(db, user.id, titulo, descripcion_corta, "incident_created", data)
                    try:
                        send_push_notification(user.fcm_token, APP_TITLE, descripcion_corta, data)
                        user_ids_sent.add(user.id)
                    except Exception:
                        logger.exception("Error notificando usuario staff %s sobre incidente creado", user.id)
            except Exception:
                logger.exception("Error notificando a user admin %s", getattr(user, "id", None))

        if not user_ids_sent:
            logger.info("No admin FCM tokens found for incident %s", incidente.id)
    except Exception:
        logger.exception("Error en notify_new_incident")


def notify_assignment_to_employee(db: Session, asignacion_id: str) -> None:
    try:
        # avoid circular import at module top; import here
        from app.db.models import AsignacionServicio, Empleado, Incidente

        asign: AsignacionServicio | None = db.get(AsignacionServicio, asignacion_id)
        if not asign:
            logger.warning("Asignacion %s no encontrada para notificar", asignacion_id)
            return

        empleado: Empleado | None = db.get(Empleado, asign.empleado_id) if asign.empleado_id else None
        if not empleado:
            logger.warning("Empleado %s no existe para asignacion %s", asign.empleado_id, asignacion_id)
            return

        # build message (include incidente.tipo if available to make notification clearer)
        titulo = "Nueva asignación"
        incidente_obj = None
        try:
            if asign.incidente_id:
                incidente_obj = db.get(Incidente, asign.incidente_id)
        except Exception:
            incidente_obj = None

        incidente_tipo = (incidente_obj.tipo if incidente_obj and getattr(incidente_obj, 'tipo', None) else None)
        if incidente_tipo:
            descripcion = f"Tienes una nueva asignación: {incidente_tipo}"
        else:
            descripcion = f"Tienes una nueva asignación (servicio: {asign.servicio_id})"

        data = {"asignacion_id": asign.id, "incidente_id": asign.incidente_id or "", "tipo": incidente_tipo or "", "titulo": titulo}

        if empleado.usuario_id:
            _store_notification(db, empleado.usuario_id, titulo, descripcion, "assignment_created", data)

        if empleado.fcm_token:
            try:
                send_push_notification(empleado.fcm_token, APP_TITLE, descripcion, data)
            except Exception:
                logger.exception("Error enviando notificación de asignación a empleado %s", empleado.id)
        else:
            logger.info("Empleado %s no tiene fcm_token, no se pudo enviar push", empleado.id)
    except Exception:
        logger.exception("Error en notify_assignment_to_employee")


def notify_assignment_to_client(db: Session, asignacion_id: str) -> None:
    try:
        from app.db.models import AsignacionServicio, Incidente, Cliente

        asign: AsignacionServicio | None = db.get(AsignacionServicio, asignacion_id)
        if not asign:
            logger.warning("Asignacion %s no encontrada para notificar al cliente", asignacion_id)
            return

        incidente: Incidente | None = db.get(Incidente, asign.incidente_id) if asign.incidente_id else None
        if not incidente or not incidente.cliente_id:
            logger.warning("Incidente/cliente no encontrado para asignacion %s", asignacion_id)
            return

        cliente: Cliente | None = db.get(Cliente, incidente.cliente_id)
        if not cliente:
            logger.warning("Cliente %s no encontrado para incidente %s", incidente.cliente_id, incidente.id)
            return

        titulo = "Tu solicitud está en proceso"
        incidente_tipo = incidente.tipo or ''
        descripcion = f"Tu solicitud de {incidente_tipo} fue asignada y está en proceso"
        data = {"incidente_id": incidente.id, "asignacion_id": asign.id, "tipo": incidente_tipo, "titulo": titulo}

        if cliente.usuario_id:
            _store_notification(db, cliente.usuario_id, titulo, descripcion, "assignment_created", data)

        if cliente.fcm_token:
            try:
                send_push_notification(cliente.fcm_token, APP_TITLE, descripcion, data)
            except Exception:
                logger.exception("Error enviando notificación de asignación al cliente %s", cliente.id)
        else:
            logger.info("Cliente %s no tiene fcm_token, no se pudo enviar push", cliente.id)
    except Exception:
        logger.exception("Error en notify_assignment_to_client")


def notify_incidente_atendido(db: Session, incidente_id: str, actor_empleado_id: str | None = None) -> None:
    """Notifica a administradores y al cliente cuando un incidente cambia a 'atendido'"""
    try:
        from app.db.models import Incidente, Empleado, Cliente, User

        incidente: Incidente | None = db.get(Incidente, incidente_id)
        if not incidente:
            logger.warning("Incidente %s no encontrado para notificar atendido", incidente_id)
            return

        tipo = incidente.tipo or ''

        # Try resolve actor name if provided
        actor_name = None
        try:
            if actor_empleado_id:
                actor_emp = db.get(Empleado, actor_empleado_id)
                if actor_emp:
                    actor_name = getattr(actor_emp, 'nombre_completo', None)
        except Exception:
            actor_name = None

        # Notify admins
        titulo_admin = "Solicitud atendida"
        if actor_name:
            descripcion_admin = f"El empleado '{actor_name}' completó su asignación"
        else:
            descripcion_admin = f"La solicitud de {tipo} (ID {incidente.id}) fue atendida"
        data_admin = {"incidente_id": incidente.id, "tipo": tipo, "estado": incidente.estado or '', "actor_nombre": actor_name or "", "titulo": titulo_admin}

        # Admin Empleados (regardless of FCM token)
        stmt_emp = select(Empleado)
        empleados = db.execute(stmt_emp).scalars().all()
        admin_emps = [e for e in empleados if (e.usuario and getattr(e.usuario, "is_staff", False)) or any("admin" in (r.nombre or "").lower() for r in (e.roles or []))]
        user_ids_sent = set()
        for emp in admin_emps:
            if not emp.usuario_id:
                continue
            if emp.usuario_id not in user_ids_sent:
                _store_notification(db, emp.usuario_id, titulo_admin, descripcion_admin, "incident_attended", data_admin)
                user_ids_sent.add(emp.usuario_id)
            if emp.fcm_token:
                try:
                    send_push_notification(emp.fcm_token, APP_TITLE, descripcion_admin, data_admin)
                except Exception:
                    logger.exception("Error notificando admin empleado %s sobre incidente atendido", emp.id)

        user_ids_sent = _notify_staff_users(db, titulo_admin, descripcion_admin, "incident_attended", data_admin, user_ids_sent)

        # Notify client
        if incidente.cliente_id:
            cliente = db.get(Cliente, incidente.cliente_id)
            if cliente:
                titulo_cli = "Tu solicitud fue atendida"
                descripcion_cli = f"Tu solicitud de {tipo} fue atendida"
                data_cli = {"incidente_id": incidente.id, "tipo": tipo, "estado": incidente.estado or '', "titulo": titulo_cli}
                if cliente.usuario_id:
                    _store_notification(db, cliente.usuario_id, titulo_cli, descripcion_cli, "incident_attended", data_cli)
                if cliente.fcm_token:
                    try:
                        send_push_notification(cliente.fcm_token, APP_TITLE, descripcion_cli, data_cli)
                    except Exception:
                        logger.exception("Error notificando cliente %s sobre incidente atendido", cliente.id)
                else:
                    logger.info("Cliente %s no tiene fcm_token para notificacion atendido", cliente.id)
    except Exception:
        logger.exception("Error en notify_incidente_atendido")


def notify_incidente_en_proceso(db: Session, incidente_id: str) -> None:
    """Notifica al cliente cuando el empleado cambia el estado a 'en_proceso'"""
    try:
        from app.db.models import Incidente, Cliente

        incidente: Incidente | None = db.get(Incidente, incidente_id)
        if not incidente:
            logger.warning("Incidente %s no encontrado para notificar en_proceso", incidente_id)
            return

        if not incidente.cliente_id:
            logger.warning("Incidente %s no tiene cliente_id", incidente_id)
            return

        cliente: Cliente | None = db.get(Cliente, incidente.cliente_id)
        if not cliente:
            logger.warning("Cliente %s no encontrado para incidente %s", incidente.cliente_id, incidente.id)
            return

        tipo = incidente.tipo or 'Tu solicitud'
        titulo = "El técnico está en camino"
        descripcion = f"El técnico asignado está en camino para atender tu {tipo}"
        data = {
            "incidente_id": incidente.id,
            "tipo": tipo,
            "estado": "en_proceso",
            "titulo": titulo,
        }

        # Store notification in DB
        if cliente.usuario_id:
            _store_notification(db, cliente.usuario_id, titulo, descripcion, "incident_in_process", data)

        # Send push notification
        if cliente.fcm_token:
            try:
                send_push_notification(cliente.fcm_token, APP_TITLE, descripcion, data)
            except Exception:
                logger.exception("Error enviando notificación en_proceso al cliente %s", cliente.id)
        else:
            logger.info("Cliente %s no tiene fcm_token, no se pudo enviar push", cliente.id)
    except Exception:
        logger.exception("Error en notify_incidente_en_proceso")


def notify_incidente_iniciado(db: Session, incidente_id: str, actor_empleado_id: str | None = None) -> None:
    """Notifica a administradores cuando un empleado marca 'en_proceso' (inició la atención)."""
    try:
        from app.db.models import Incidente, Empleado

        incidente: Incidente | None = db.get(Incidente, incidente_id)
        if not incidente:
            logger.warning("Incidente %s no encontrado para notificar inicio", incidente_id)
            return

        tipo = incidente.tipo or ''

        # Resolve actor name if provided
        actor_name = None
        try:
            if actor_empleado_id:
                actor_emp = db.get(Empleado, actor_empleado_id)
                if actor_emp:
                    actor_name = getattr(actor_emp, 'nombre_completo', None)
        except Exception:
            actor_name = None

        titulo_admin = "Técnico en camino"
        if actor_name:
            descripcion_admin = f"El técnico '{actor_name}' inició la atención de la solicitud"
        else:
            descripcion_admin = f"La solicitud de {tipo} ha comenzado (incidente {incidente.id})"

        data_admin = {"incidente_id": incidente.id, "tipo": tipo, "estado": "en_proceso", "actor_nombre": actor_name or "", "titulo": titulo_admin}

        # Admin Empleados (regardless of FCM token)
        stmt_emp = select(Empleado)
        empleados = db.execute(stmt_emp).scalars().all()
        admin_emps = [e for e in empleados if (e.usuario and getattr(e.usuario, "is_staff", False)) or any("admin" in (r.nombre or "").lower() for r in (e.roles or []))]
        user_ids_sent = set()
        for emp in admin_emps:
            if not emp.usuario_id:
                continue
            if emp.usuario_id not in user_ids_sent:
                _store_notification(db, emp.usuario_id, titulo_admin, descripcion_admin, "incident_started", data_admin)
                user_ids_sent.add(emp.usuario_id)
            if emp.fcm_token:
                try:
                    send_push_notification(emp.fcm_token, APP_TITLE, descripcion_admin, data_admin)
                except Exception:
                    logger.exception("Error notificando admin empleado %s sobre inicio de incidente", emp.id)

        _notify_staff_users(db, titulo_admin, descripcion_admin, "incident_started", data_admin, user_ids_sent)
    except Exception:
        logger.exception("Error en notify_incidente_iniciado")