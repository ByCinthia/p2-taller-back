from __future__ import annotations

import logging
import math
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.db.models import Cliente, Diagnostico, Empleado, Empresa, Evidencia, Incidente, Servicio, Vehiculo
from app.schemas.incidente import (
    IncidenteCreate,
    IncidenteUpdate,
    TallerCercanoOut,
    TecnicoCercanoOut,
    TecnicoUbicacionUpdate,
)
from app.services.asignacion_service import (
    close_active_asignacion_for_incidente,
    create_asignacion,
    get_active_asignacion_for_incidente,
)
from app.services.notification_service import notify_assignment_to_employee, notify_incidente_en_proceso, notify_new_incident

logger = logging.getLogger(__name__)


def _distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_km = 6371.0
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lon / 2) ** 2
    )
    return 2 * radius_km * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def list_incidentes(db: Session) -> list[Incidente]:
    return db.execute(select(Incidente).order_by(Incidente.creado_en.desc())).scalars().all()


def create_incidente(db: Session, payload: IncidenteCreate, cliente_id: str | None = None) -> Incidente:
    obj = Incidente(
        id=str(uuid.uuid4()),
        cliente_id=cliente_id,
        vehiculo_id=payload.vehiculo_id,
        tipo=payload.tipo,
        descripcion=payload.descripcion,
        estado="pendiente",
        prioridad=payload.prioridad,
        latitud=payload.latitud,
        longitud=payload.longitud,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    # notify admins that a new incident/solicitud was created
    try:
        notify_new_incident(db, obj)
    except Exception:
        # do not fail creation if notification fails
        pass

    return obj


def get_incidente_or_404(db: Session, incidente_id: str) -> Incidente:
    obj = db.get(Incidente, incidente_id)
    if not obj:
        raise ValueError("Incidente no encontrado")
    return obj


def update_incidente(db: Session, incidente: Incidente, payload: IncidenteUpdate) -> Incidente:
    if payload.estado is not None:
        estado_recibido = payload.estado
        target_state = estado_recibido
        
        # Nota: en_camino/en_sitio/en_proceso son etapas visuales, no estados persistidos
        mapeado = False
        if target_state in {"en_camino", "en_sitio", "en_proceso"}:
            target_state = "aceptada"
            mapeado = True
        elif target_state == "finalizado":
            target_state = "atendido"
            mapeado = True
            
        logger.info(f"[incidente_service] update_incidente: estado_recibido='{estado_recibido}', estado_guardado='{target_state}', mapeado={mapeado}")
        
        valid_states = {"pendiente", "aceptada", "asignada", "atendido", "completada", "cancelada"}
        if target_state in valid_states:
            incidente.estado = target_state
        else:
            logger.warning(f"[incidente_service] Intento de guardar estado invalido en BD: '{target_state}'")
    if payload.prioridad is not None:
        incidente.prioridad = payload.prioridad
    if payload.descripcion is not None:
        incidente.descripcion = payload.descripcion
    # ETA / tiempo estimado now belongs to asignacion_servicio and is not
    # stored on the incidente record.

    db.add(incidente)
    db.commit()
    db.refresh(incidente)
    return incidente


def assign_tecnico(
    db: Session,
    incidente: Incidente,
    empleado_id: str | None = None,
    servicio_id: str | None = None,
    actor: Empleado | None = None,
) -> Incidente:
    # Create an operational assignment record (asignacion_servicio) instead of
    # mutating the incidente table. The assignment service will validate the
    # empleado and set empresa_id automatically.
    empleado: Empleado | None = None
    if empleado_id:
        empleado = db.get(Empleado, empleado_id)
        if not empleado:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empleado no encontrado")
        if actor and actor.empresa_id != empleado.empresa_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No puedes asignar técnicos de otro taller")
    else:
        # pick any employee in the same empresa as actor if provided,
        # otherwise any employee
        stmt = select(Empleado)
        if actor:
            stmt = stmt.where(Empleado.empresa_id == actor.empresa_id)
        candidato = db.execute(stmt).scalars().first()
        if not candidato:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No hay técnicos para asignar")
        empleado = candidato

    asign = create_asignacion(
        db,
        incidente=incidente,
        empleado_id=empleado.id,
        servicio_id=servicio_id,
        empresa_id=empleado.empresa_id,
    )
    if incidente.estado == "pendiente":
        incidente.estado = "asignada"
        db.add(incidente)
        db.commit()
        db.refresh(incidente)

    # notify the assigned employee (push)
    try:
        notify_assignment_to_employee(db, asign.id)
    except Exception:
        # do not fail assignment if notification fails
        pass
    # Notificación al cliente ahora se envía cuando empleado cambia a "en_proceso"
    # (no cuando se asigna, solo cuando está en camino)

    # return incidente (unchanged except estado)
    return incidente


def update_tecnico_ubicacion(db: Session, empleado: Empleado, payload: TecnicoUbicacionUpdate) -> Empleado:
    empleado.latitud_actual = payload.latitud
    empleado.longitud_actual = payload.longitud
    empleado.ubicacion_actualizada_en = datetime.now(timezone.utc)
    if payload.disponible is not None:
        empleado.disponible = payload.disponible

    db.add(empleado)
    db.commit()
    db.refresh(empleado)
    return empleado


def update_incidente_tecnico_ubicacion(db: Session, incidente: Incidente, empleado: Empleado, payload: TecnicoUbicacionUpdate) -> Empleado:
    # Only the active assigned technician for the incidente may update location
    asign = get_active_asignacion_for_incidente(db, incidente.id)
    if not asign or asign.empleado_id != empleado.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo el técnico asignado puede actualizar esta ubicación")
    return update_tecnico_ubicacion(db, empleado, payload)


def get_incidente_tracking(db: Session, incidente: Incidente) -> dict:
    asign = get_active_asignacion_for_incidente(db, incidente.id)
    tecnico = db.get(Empleado, asign.empleado_id) if asign else None

    from app.services.tracking_ws import tracking_ws_manager
    visual_state = tracking_ws_manager.visual_states.get(incidente.id)
    current_state = visual_state if visual_state else incidente.estado

    dist_km = None
    eta_m = None
    if incidente.latitud is not None and incidente.longitud is not None and tecnico and tecnico.latitud_actual is not None and tecnico.longitud_actual is not None:
        try:
            dist_km = round(_distance_km(float(incidente.latitud), float(incidente.longitud), float(tecnico.latitud_actual), float(tecnico.longitud_actual)), 3)
            eta_m = int(dist_km * 2)
        except Exception:
            pass

    return {
        "incidente_id": incidente.id,
        "estado": current_state,
        "latitud_incidente": float(incidente.latitud) if incidente.latitud is not None else None,
        "longitud_incidente": float(incidente.longitud) if incidente.longitud is not None else None,
        "asignacion_id": asign.id if asign else None,
        "empleado_id": tecnico.id if tecnico else None,
        "tecnico_nombre": tecnico.nombre_completo if tecnico else None,
        "tecnico_latitud": float(tecnico.latitud_actual) if tecnico and tecnico.latitud_actual is not None else None,
        "tecnico_longitud": float(tecnico.longitud_actual) if tecnico and tecnico.longitud_actual is not None else None,
        "tecnico_disponible": tecnico.disponible if tecnico else None,
        "tecnico_ubicacion_actualizada_en": tecnico.ubicacion_actualizada_en.isoformat() if tecnico and tecnico.ubicacion_actualizada_en else None,
        "distancia_km": dist_km,
        "eta_minutos": eta_m,
    }


def list_tecnicos_disponibles(
    db: Session,
    empresa_id: str | None = None,
    latitud: float | None = None,
    longitud: float | None = None,
    radio_km: float | None = None,
) -> list:
    """
    Retorna la lista de técnicos disponibles, manejando valores nulos
    y excluyendo al personal administrativo.
    """
    
    # 1. Consulta base filtrando por empresa; la disponibilidad real se define por no tener asignación activa
    stmt = select(Empleado).options(
        joinedload(Empleado.usuario),
        joinedload(Empleado.cargo),
        joinedload(Empleado.roles),
    )

    if empresa_id:
        stmt = stmt.where(Empleado.empresa_id == empresa_id)

    candidatos = db.execute(stmt).unique().scalars().all()
    resultados = []
    admin_aliases = {"admin", "administrador"}

    for tecnico in candidatos:
        # Omitir si es administrador por cargo, rol o cuenta staff/superuser
        cargo_obj = getattr(tecnico, 'cargo', None)
        cargo_nombre = (getattr(cargo_obj, 'nombre', '') or '').strip().lower()
        if cargo_nombre in admin_aliases:
            continue

        if getattr(getattr(tecnico, 'usuario', None), 'is_staff', False) or getattr(getattr(tecnico, 'usuario', None), 'is_superuser', False):
            continue

        roles = getattr(tecnico, 'roles', []) or []
        if any((getattr(role, 'nombre', '') or '').strip().lower() in admin_aliases for role in roles):
            continue

        # Mapeo del nombre (priorizando el nombre completo del empleado)
        nombre_display = getattr(tecnico, 'nombre_completo', None)
        
        if not nombre_display and hasattr(tecnico, 'usuario') and tecnico.usuario:
            u = tecnico.usuario
            nombre_display = f"{getattr(u, 'first_name', '')} {getattr(u, 'last_name', '')}".strip()
            
            if not nombre_display:
                nombre_display = getattr(u, 'username', 'Técnico sin nombre')

        try:
            # Manejo seguro de coordenadas
            t_lat = getattr(tecnico, 'latitud_actual', None)
            t_lon = getattr(tecnico, 'longitud_actual', None)

            distancia = None
            eta = None

            t_lat_float = float(t_lat) if t_lat is not None else None
            t_lon_float = float(t_lon) if t_lon is not None else None

            if latitud is not None and longitud is not None and t_lat_float is not None and t_lon_float is not None:
                if t_lat_float != 0.0 or t_lon_float != 0.0:
                    distancia = round(_distance_km(latitud, longitud, t_lat_float, t_lon_float), 3)
                    eta = round(distancia * 2)

            resultados.append({
                "id": str(tecnico.id),
                "empleado_id": str(tecnico.id),
                "nombre_completo": nombre_display or "Técnico Disponible",
                "disponible": True,
                "latitud_actual": t_lat_float,
                "longitud_actual": t_lon_float,
                "latitud": t_lat_float,
                "longitud": t_lon_float,
                "distancia_km": distancia,
                "tiempo_estimado_llegada_minutos": eta,
                "eta_minutos": eta,
            })
        except Exception as e:
            logger.error(f"Error procesando tecnico {tecnico.id}: {e}")
            resultados.append({
                "id": str(tecnico.id),
                "empleado_id": str(tecnico.id),
                "nombre_completo": nombre_display or "Técnico Disponible",
                "disponible": True,
                "latitud_actual": None,
                "longitud_actual": None,
                "latitud": None,
                "longitud": None,
                "distancia_km": None,
                "tiempo_estimado_llegada_minutos": None,
                "eta_minutos": None,
            })

    # Sort: first those with location (and distance), sorted by distance.
    # Those without location go at the end.
    def sort_key(x):
        if x["distancia_km"] is not None:
            return (0, x["distancia_km"])
        return (1, float('inf'))

    resultados.sort(key=sort_key)

    if latitud is not None and longitud is not None:
        logger.info(f"[tecnicos_disponibles] latitud={latitud} longitud={longitud} cantidad_encontrados={len(resultados)}")
        for idx, r in enumerate(resultados[:5]):
            logger.info(f"   {idx+1}. {r['nombre_completo']} - dist: {r['distancia_km']} km")

    return resultados

def list_tecnicos_cercanos(
    db: Session,
    latitud: float,
    longitud: float,
    radio_km: float,
    empresa_id: str | None = None,
) -> list[TecnicoCercanoOut]:
    stmt = select(Empleado).options(
        joinedload(Empleado.usuario),
        joinedload(Empleado.cargo),
        joinedload(Empleado.roles),
    ).where(
        Empleado.latitud_actual.isnot(None),
        Empleado.longitud_actual.isnot(None),
    )
    if empresa_id:
        stmt = stmt.where(Empleado.empresa_id == empresa_id)

    candidatos = db.execute(stmt).unique().scalars().all()
    resultados: list[TecnicoCercanoOut] = []
    admin_aliases = {"admin", "administrador"}

    for tecnico in candidatos:
        cargo_obj = getattr(tecnico, 'cargo', None)
        cargo_nombre = (getattr(cargo_obj, 'nombre', '') or '').strip().lower()
        if cargo_nombre in admin_aliases:
            continue

        if getattr(getattr(tecnico, 'usuario', None), 'is_staff', False) or getattr(getattr(tecnico, 'usuario', None), 'is_superuser', False):
            continue

        roles = getattr(tecnico, 'roles', []) or []
        if any((getattr(role, 'nombre', '') or '').strip().lower() in admin_aliases for role in roles):
            continue

        tecnico_lat = float(tecnico.latitud_actual)
        tecnico_lon = float(tecnico.longitud_actual)
        distancia = _distance_km(latitud, longitud, tecnico_lat, tecnico_lon)
        if distancia <= radio_km:
            resultados.append(
                TecnicoCercanoOut(
                    empleado_id=tecnico.id,
                    nombre_completo=tecnico.nombre_completo,
                    latitud=tecnico_lat,
                    longitud=tecnico_lon,
                    distancia_km=round(distancia, 3),
                    disponible=True,
                )
            )

    resultados.sort(key=lambda item: item.distancia_km)
    return resultados



def add_diagnostico(db: Session, incidente: Incidente, clasificacion: int | None = None, resumen: str | None = None, prioridad: int | None = None) -> Diagnostico:
    diag = Diagnostico(
        incidente_id=incidente.id,
        clasificacion=clasificacion,
        resumen=resumen,
        prioridad=prioridad,
        creado_en=datetime.now(timezone.utc),
    )
    db.add(diag)
    db.commit()
    db.refresh(diag)
    return diag


def add_evidencia(db: Session, incidente: Incidente, tipo: str, url_archivo: str | None = None, texto: str | None = None) -> Evidencia:
    ev = Evidencia(incidente_id=incidente.id, tipo=tipo, url_archivo=url_archivo, texto=texto)
    db.add(ev)
    db.commit()
    db.refresh(ev)
    return ev


def list_evidencias_for_incidente(db: Session, incidente_id: str) -> list[Evidencia]:
    stmt = select(Evidencia).where(Evidencia.incidente_id == incidente_id)
    return db.execute(stmt).scalars().all()


def get_evidencia_or_404(db: Session, evidencia_id: str) -> Evidencia:
    obj = db.get(Evidencia, evidencia_id)
    if not obj:
        raise ValueError("Evidencia no encontrada")
    return obj


def delete_evidencia(db: Session, evidencia: Evidencia) -> None:
    db.delete(evidencia)
    db.commit()


def list_diagnosticos_for_incidente(db: Session, incidente_id: str) -> list[Diagnostico]:
    stmt = select(Diagnostico).where(Diagnostico.incidente_id == incidente_id)
    return db.execute(stmt).scalars().all()


def get_diagnostico_or_404(db: Session, diagnostico_id: str) -> Diagnostico:
    obj = db.get(Diagnostico, diagnostico_id)
    if not obj:
        raise ValueError("Diagnostico no encontrado")
    return obj


def update_diagnostico(db: Session, diagnostico: Diagnostico, clasificacion: int | None = None, resumen: str | None = None, prioridad: int | None = None) -> Diagnostico:
    if clasificacion is not None:
        diagnostico.clasificacion = clasificacion
    if resumen is not None:
        diagnostico.resumen = resumen
    if prioridad is not None:
        diagnostico.prioridad = prioridad
    db.add(diagnostico)
    db.commit()
    db.refresh(diagnostico)
    return diagnostico


# ============================================================
# FASE 1 — Asignación de Talleres
# ============================================================

def find_talleres_cercanos(
    db: Session,
    latitud: float,
    longitud: float,
    radio_km: float = 5.0,
    servicio_tipo: str | None = None,
) -> list[TallerCercanoOut]:
    """Busca talleres (empresas) cercanos al punto dado.

    Criterios:
    3.1  Radio de ``radio_km`` (default 5 km).
    3.2  Si se indica ``servicio_tipo``, solo talleres con un servicio
         cuyo nombre contenga ese texto (case-insensitive).
    3.4  Ordenados por puntuación (estrellas_promedio) descendente,
         luego por distancia ascendente.
    """
    stmt = select(Empresa).where(
        Empresa.latitud.isnot(None),
        Empresa.longitud.isnot(None),
    )

    # 3.2 Filtrar por servicio ofrecido
    if servicio_tipo:
        stmt = stmt.join(Servicio, Servicio.empresa_id == Empresa.id).where(
            Servicio.activo == True,  # noqa: E712
            Servicio.nombre.ilike(f"%{servicio_tipo}%"),
        )

    # 3.4 Ordenar por puntuación alta primero
    stmt = stmt.order_by(Empresa.estrellas_promedio.desc())

    empresas = db.execute(stmt).unique().scalars().all()

    resultados: list[TallerCercanoOut] = []
    for emp in empresas:
        distancia = _distance_km(latitud, longitud, float(emp.latitud), float(emp.longitud))
        if distancia <= radio_km:
            # Recolectar nombres de servicios del taller
            svc_stmt = select(Servicio).where(Servicio.empresa_id == emp.id, Servicio.activo == True)  # noqa: E712
            servicios_nombres = [s.nombre for s in db.execute(svc_stmt).scalars().all()]

            resultados.append(
                TallerCercanoOut(
                    empresa_id=emp.id,
                    nombre=emp.nombre,
                    latitud=float(emp.latitud),
                    longitud=float(emp.longitud),
                    distancia_km=round(distancia, 3),
                    estrellas_promedio=float(emp.estrellas_promedio),
                    total_calificaciones=emp.total_calificaciones,
                    servicios=servicios_nombres,
                )
            )

    # Ordenar por rating descendente, luego distancia ascendente
    resultados.sort(key=lambda t: (-t.estrellas_promedio, t.distancia_km))
    return resultados


def auto_asignar_taller(
    db: Session,
    incidente: Incidente,
    radio_km: float = 5.0,
) -> TallerCercanoOut | None:
    """Encuentra el mejor taller para el incidente y lo acepta automáticamente.

    Retorna el taller asignado o ``None`` si no se encontró ninguno.
    """
    if incidente.estado != "pendiente":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se pueden auto-asignar incidentes pendientes",
        )
    if incidente.latitud is None or incidente.longitud is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El incidente no tiene ubicación para buscar talleres cercanos",
        )

    talleres = find_talleres_cercanos(
        db,
        latitud=float(incidente.latitud),
        longitud=float(incidente.longitud),
        radio_km=radio_km,
        servicio_tipo=incidente.tipo,
    )

    if not talleres:
        return None

    mejor_taller = talleres[0]

    # Aceptar el incidente para este taller
    incidente.estado = "aceptada"
    incidente.accepted_empresa_id = mejor_taller.empresa_id
    db.add(incidente)
    db.commit()
    db.refresh(incidente)

    # Gamificación: +5 estrellas por aceptar
    from app.services.gamificacion_service import register_sistema_rating_for_empresa
    try:
        register_sistema_rating_for_empresa(db, mejor_taller.empresa_id, 5)
    except Exception:
        logger.exception("Error registrando rating por auto-asignación")

    # Notificar al taller asignado
    _notify_empresa_new_incident(db, mejor_taller.empresa_id, incidente)

    return mejor_taller


def _notify_empresa_new_incident(db: Session, empresa_id: str, incidente: Incidente) -> None:
    """Envía notificación solo a los empleados admin/staff de una empresa específica."""
    import json
    import logging as _logging
    from app.db.models import Notificacion

    _logger = _logging.getLogger(__name__)

    titulo = "Nueva solicitud asignada"
    descripcion = f"{incidente.tipo or 'Incidente'}"
    if incidente.descripcion:
        descripcion = f"{descripcion} - {incidente.descripcion[:60]}"
    data = {"incidente_id": incidente.id, "tipo": incidente.tipo or "", "estado": incidente.estado or ""}

    stmt = select(Empleado).where(Empleado.empresa_id == empresa_id)
    empleados = db.execute(stmt).scalars().all()

    for emp in empleados:
        if not emp.usuario_id:
            continue
        # Solo notificar a admins/staff de la empresa
        is_admin = (
            (emp.usuario and getattr(emp.usuario, "is_staff", False))
            or any("admin" in (r.nombre or "").lower() for r in (emp.roles or []))
        )
        if not is_admin:
            continue

        try:
            notif = Notificacion(
                id=str(uuid.uuid4()),
                user_id=emp.usuario_id,
                titulo=titulo,
                mensaje=descripcion,
                tipo="incident_assigned",
                data_json=json.dumps(data, ensure_ascii=False),
            )
            db.add(notif)
            db.commit()
            db.refresh(notif)

            # FCM push
            if emp.fcm_token:
                try:
                    from app.services.notification_service import send_push_notification
                    send_push_notification(emp.fcm_token, titulo, descripcion, data)
                except Exception:
                    _logger.exception("Error enviando FCM a empleado %s", emp.id)
        except Exception:
            _logger.exception("Error guardando notificación para empleado %s", emp.id)


__all__ = [
    "list_incidentes",
    "create_incidente",
    "get_incidente_or_404",
    "update_incidente",
    "assign_tecnico",
    "update_tecnico_ubicacion",
    "update_incidente_tecnico_ubicacion",
    "get_incidente_tracking",
    "list_tecnicos_cercanos",
    "add_diagnostico",
    "add_evidencia",
    "find_talleres_cercanos",
    "auto_asignar_taller",
]
