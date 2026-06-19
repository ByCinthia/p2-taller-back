from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, WebSocket, WebSocketDisconnect, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.deps.auth import get_current_employee, get_current_user, require_permission
from app.schemas.incidente import (
    AsignarTecnicoRequest,
    AutoAsignarResponse,
    IncidenteCreate,
    IncidenteOut,
    IncidenteTrackingOut,
    IncidenteUpdate,
    IncidentePatchEstado,
    TallerCercanoOut,
    TecnicoCercanoOut,
    TecnicoUbicacionUpdate,
)
from app.services.cliente_service import get_cliente_for_user
from app.services.permission_service import resolve_employee, has_named_permission
from app.services.incidente_service import (
    assign_tecnico,
    auto_asignar_taller,
    close_active_asignacion_for_incidente,
    find_talleres_cercanos,
    list_incidentes,
    list_tecnicos_disponibles,
    create_incidente,
    get_incidente_or_404,
    get_incidente_tracking,
    update_incidente,
    update_incidente_tecnico_ubicacion,
    update_tecnico_ubicacion,
    add_diagnostico,
    add_evidencia,
    list_diagnosticos_for_incidente,
    get_diagnostico_or_404,
    update_diagnostico,
    _distance_km,
)
from app.services.asignacion_service import get_active_asignacion_for_incidente
from app.services.file_storage import save_incidente_evidence
from app.services.gamificacion_service import register_sistema_rating_for_empresa
from app.services.tracking_ws import tracking_ws_manager
from app.services.cloudinary_service import upload_evidence as cloudinary_upload_evidence
from app.services.transcription_service import transcribe_audio
import tempfile
import os
import shutil
import logging
logger = logging.getLogger(__name__)
router = APIRouter(prefix="/incidentes", tags=["incidentes"])
settings = get_settings()


# ============================================================
# CRUD BÁSICO
# ============================================================

def _populate_assignment(db: Session, inc) -> None:
    asign = get_active_asignacion_for_incidente(db, inc.id)
    if asign:
        inc.tecnico_asignado_id = asign.empleado_id
        if asign.empleado:
            nombre = asign.empleado.nombre_completo
            if not nombre and asign.empleado.usuario:
                nombre = f"{asign.empleado.usuario.first_name or ''} {asign.empleado.usuario.last_name or ''}".strip()
            inc.tecnico_asignado_nombre = nombre or "Técnico"
        inc.estado_asignacion = asign.estado_tarea
        # No 'servicio' relation natively, but if it exists we can try:
        if hasattr(asign, "servicio") and asign.servicio:
            inc.servicio_asignado = asign.servicio.nombre
            
        # Calcular distancia y ETA si hay coordenadas
        if getattr(inc, "latitud", None) is not None and getattr(inc, "longitud", None) is not None:
            t_lat = getattr(asign.empleado, "latitud_actual", None)
            t_lon = getattr(asign.empleado, "longitud_actual", None)
            
            if t_lat is not None and t_lon is not None:
                t_lat_float = float(t_lat)
                t_lon_float = float(t_lon)
                i_lat_float = float(inc.latitud)
                i_lon_float = float(inc.longitud)
                
                if (t_lat_float != 0.0 or t_lon_float != 0.0) and (i_lat_float != 0.0 or i_lon_float != 0.0):
                    try:
                        distancia = round(_distance_km(i_lat_float, i_lon_float, t_lat_float, t_lon_float), 3)
                        inc.distancia_km = distancia
                        inc.eta_minutos = int(distancia * 2)
                    except Exception as e:
                        logger.error(f"Error calculating distance for assignment {asign.id}: {e}")
                        inc.distancia_km = None
                        inc.eta_minutos = None

@router.get("/", response_model=list[IncidenteOut])
def incidentes_list(user=Depends(get_current_user), db: Session = Depends(get_db)) -> list[IncidenteOut]:
    """Listar todos los incidentes (requiere autenticación)"""
    incidentes = list_incidentes(db)
    # Populate active assignments for response
    for inc in incidentes:
        _populate_assignment(db, inc)
    return incidentes


#@router.get("/tecnicos/cercanos", response_model=list[TecnicoCercanoOut])
#def tecnicos_cercanos(
 #   latitud: float = Query(..., ge=-90, le=90),
  #  longitud: float = Query(..., ge=-180, le=180),
  #  radio_km: float = Query(default=5, gt=0, le=100),
  #  user=Depends(get_current_user),
  #  db: Session = Depends(get_db),
#) -> list[TecnicoCercanoOut]:
 #   actor = resolve_employee(db, user)
 #   empresa_id = None if user.is_staff else (actor.empresa_id if actor else None)
 #   return list_tecnicos_cercanos(db, latitud=latitud, longitud=longitud, radio_km=radio_km, empresa_id=empresa_id)

@router.get("/tecnicos/disponibles", response_model=list[TecnicoCercanoOut])
def tecnicos_disponibles(
    # Cambiamos los parámetros a opcionales (None) para que no bloqueen la petición
    latitud: float | None = Query(None, ge=-90, le=90),
    longitud: float | None = Query(None, ge=-180, le=180),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[TecnicoCercanoOut]:
    # Para pruebas de asignación mostramos todos los empleados libres no administrativos.
    # Esto evita que una empresa sin técnicos libres quede con una lista vacía.
    return list_tecnicos_disponibles(db, empresa_id=None, latitud=latitud, longitud=longitud)

@router.post("/", response_model=IncidenteOut, status_code=status.HTTP_201_CREATED)
def incidentes_create(payload: IncidenteCreate, user=Depends(get_current_user), db: Session = Depends(get_db)) -> IncidenteOut:
    cliente_id = None
    cliente = get_cliente_for_user(db, user.id)
    if cliente:
        cliente_id = cliente.id

    inc = create_incidente(db, payload, cliente_id=cliente_id)
    _populate_assignment(db, inc)
    return inc


@router.post("/{incidente_id}/asignacion", response_model=IncidenteOut)
async def incidentes_asignar_tecnico(
    incidente_id: str,
    payload: AsignarTecnicoRequest,
    user=Depends(require_permission("manage_incidentes")),
    db: Session = Depends(get_db),
) -> IncidenteOut:
    try:
        inc = get_incidente_or_404(db, incidente_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incidente no encontrado")

    actor = resolve_employee(db, user)
    updated = assign_tecnico(db, inc, payload.empleado_id, servicio_id=payload.servicio_id, actor=actor)

    # Evento B: notificar al cliente que un técnico fue asignado
    try:
        from app.services.notification_service import notify_assignment_to_client
        # Resolver el id de la asignación recién creada
        from app.services.asignacion_service import get_active_asignacion_for_incidente
        asign_nueva = get_active_asignacion_for_incidente(db, updated.id)
        if asign_nueva:
            logger.info(
                "[asignar-tecnico] evento=B incidente_id=%s asignacion_id=%s "
                "empleado_id=%s → notificando al cliente",
                updated.id, asign_nueva.id, asign_nueva.empleado_id,
            )
            notify_assignment_to_client(db, asign_nueva.id)
    except Exception:
        logger.exception("Error notificando al cliente sobre asignación de técnico")

    tracking = get_incidente_tracking(db, updated)
    await tracking_ws_manager.broadcast(
        updated.id,
        {
            "event": "assignment_updated",
            "tracking": tracking,
        },
    )
    _populate_assignment(db, updated)
    return updated



@router.post("/{incidente_id}/aceptar-solicitud", response_model=IncidenteOut)
def incidentes_aceptar_solicitud(
    incidente_id: str,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> IncidenteOut:
    """Acepta la solicitud.

    Autorización dual:
    - Admin/supervisor con permiso manage_incidentes: pasa directo.
    - Técnico/empleado asignado: debe tener una AsignacionServicio activa
      (estado_tarea='asignada') para este incidente.
    """
    from sqlalchemy import select as sa_select
    from app.db.models import AsignacionServicio as AsignSvc

    logger.info("[aceptar-solicitud] user_id=%s incidente_id=%s", user.id, incidente_id)

    try:
        inc = get_incidente_or_404(db, incidente_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incidente no encontrado")

    actor = resolve_employee(db, user)
    logger.info("[aceptar-solicitud] empleado encontrado=%s", actor.id if actor else None)

    es_admin = has_named_permission(db, user, "manage_incidentes")

    # Buscar asignación del empleado actual para este incidente
    asignacion_propia: AsignSvc | None = None
    if actor:
        stmt = sa_select(AsignSvc).where(
            AsignSvc.incidente_id == incidente_id,
            AsignSvc.empleado_id == actor.id,
            AsignSvc.estado_tarea.in_(["asignada", "pendiente"]),
        ).limit(1)
        asignacion_propia = db.execute(stmt).scalars().first()
        logger.info(
            "[aceptar-solicitud] asignacion_propia=%s",
            asignacion_propia.id if asignacion_propia else None,
        )

    if not es_admin and not asignacion_propia:
        logger.warning(
            "[aceptar-solicitud] DENEGADO user_id=%s incidente_id=%s "
            "(no es admin ni tiene asignacion activa)",
            user.id, incidente_id,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para aceptar esta solicitud. "
                   "Solo un administrador o el técnico asignado puede aceptarla.",
        )

    logger.info("[aceptar-solicitud] AUTORIZADO user_id=%s es_admin=%s", user.id, es_admin)

    # Actualizar estado del incidente
    inc.estado = "aceptada"
    if actor:
        inc.accepted_empresa_id = actor.empresa_id
    db.add(inc)

    # Si es el técnico asignado, marcar su asignación como aceptada
    if asignacion_propia:
        asignacion_propia.estado_tarea = "aceptada"
        db.add(asignacion_propia)
        logger.info(
            "[aceptar-solicitud] AsignacionServicio %s → estado_tarea='aceptada'",
            asignacion_propia.id,
        )

    db.commit()
    db.refresh(inc)

    # Gamificación: rating 5 por aceptación
    if actor:
        try:
            register_sistema_rating_for_empresa(db, actor.empresa_id, 5)
        except Exception:
            logger.exception("Error registrando rating 5 por aceptación")

    # Notificar al cliente móvil: evento correcto según quién acepta
    try:
        from app.services.notification_service import (
            notify_incidente_aceptada,
            notify_tecnico_acepta_asignacion,
        )
        if asignacion_propia and actor:
            # Evento C: el técnico asignado aceptó su propia asignación
            logger.info(
                "[aceptar-solicitud] evento=C tecnico_acepta "
                "incidente_id=%s empleado_id=%s",
                inc.id, actor.id,
            )
            notify_tecnico_acepta_asignacion(db, inc.id, empleado_id=actor.id)
        else:
            # Evento A: admin/supervisor del taller aceptó la solicitud (sin asignación de técnico aún)
            logger.info(
                "[aceptar-solicitud] evento=A taller_acepta "
                "incidente_id=%s user_id=%s",
                inc.id, user.id,
            )
            notify_incidente_aceptada(db, inc.id)
    except Exception:
        logger.exception("Error notificando aceptación de incidente %s", inc.id)

    _populate_assignment(db, inc)
    return inc


@router.post("/{incidente_id}/cancelar-aceptacion", response_model=IncidenteOut)
def incidentes_cancelar_aceptacion(incidente_id: str, user=Depends(require_permission("manage_incidentes")), db: Session = Depends(get_db)) -> IncidenteOut:
    """Taller cancela la aceptación antes de asignar técnico."""
    try:
        inc = get_incidente_or_404(db, incidente_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incidente no encontrado")

    actor = resolve_employee(db, user)
    empresa_id = actor.empresa_id if actor else None

    # only allow cancel if accepted by this empresa
    if inc.accepted_empresa_id and empresa_id and inc.accepted_empresa_id != empresa_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No puedes cancelar una aceptación de otro taller")

    inc.estado = 'pendiente'
    inc.accepted_empresa_id = None
    db.add(inc)
    db.commit()
    db.refresh(inc)

    # penalize the workshop with 1 star
    try:
        if empresa_id:
            register_sistema_rating_for_empresa(db, empresa_id, 1)
    except Exception:
        logger.exception("Error registrando penalización por cancelación")

    _populate_assignment(db, inc)
    return inc


@router.post("/{incidente_id}/ignorar", response_model=dict)
def incidentes_ignorar(incidente_id: str, payload: dict, db: Session = Depends(get_db)) -> dict:
    """Endpoint llamado por la UI cuando el temporizador expira: payload debe incluir 'empresa_id' para penalizar."""
    empresa_id = payload.get('empresa_id')
    if not empresa_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="empresa_id requerido")
    try:
        register_sistema_rating_for_empresa(db, empresa_id, 1)
    except Exception:
        logger.exception("Error registrando penalización por ignorar alerta")
    return {"message": "penalizacion_aplicada"}


@router.get("/{incidente_id}/", response_model=IncidenteOut)
def incidentes_retrieve(
    incidente_id: str,
    db: Session = Depends(get_db)
) -> IncidenteOut:
    """Obtener detalle de un incidente"""
    try:
        inc = get_incidente_or_404(db, incidente_id)
        _populate_assignment(db, inc)
        return inc
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incidente no encontrado")


@router.patch("/{incidente_id}/", response_model=IncidenteOut)
async def incidentes_update(incidente_id: str, payload: IncidenteUpdate, user=Depends(require_permission("manage_incidentes")), db: Session = Depends(get_db)) -> IncidenteOut:
    try:
        inc = get_incidente_or_404(db, incidente_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incidente no encontrado")
    updated = update_incidente(db, inc, payload)
    tracking = get_incidente_tracking(db, updated)
    await tracking_ws_manager.broadcast(
        updated.id,
        {
            "event": "incident_updated",
            "tracking": tracking,
        },
    )
    _populate_assignment(db, updated)
    return updated


@router.patch("/tecnicos/mi-ubicacion", response_model=dict)
async def tecnicos_actualizar_mi_ubicacion(
    payload: TecnicoUbicacionUpdate,
    empleado=Depends(get_current_employee),
    db: Session = Depends(get_db),
) -> dict:
    updated = update_tecnico_ubicacion(db, empleado, payload)

    # broadcast location updates only for incidents where this technician
    # is actively assigned via asignacion_servicio
    incidentes_asignados = list_incidentes(db)
    for inc in incidentes_asignados:
        asign = get_active_asignacion_for_incidente(db, inc.id)
        if not asign or asign.empleado_id != updated.id:
            continue

        tracking = get_incidente_tracking(db, inc)
        await tracking_ws_manager.broadcast(
            inc.id,
            {
                "event": "technician_location_updated",
                "tracking": tracking,
            },
        )

    return {
        "empleado_id": updated.id,
        "latitud": float(updated.latitud_actual) if updated.latitud_actual is not None else None,
        "longitud": float(updated.longitud_actual) if updated.longitud_actual is not None else None,
        "disponible": updated.disponible,
        "ubicacion_actualizada_en": updated.ubicacion_actualizada_en.isoformat() if updated.ubicacion_actualizada_en else None,
    }


@router.patch("/{incidente_id}/tecnico/ubicacion", response_model=dict)
async def incidentes_actualizar_ubicacion_tecnico(
    incidente_id: str,
    payload: TecnicoUbicacionUpdate,
    empleado=Depends(get_current_employee),
    db: Session = Depends(get_db),
) -> dict:
    try:
        inc = get_incidente_or_404(db, incidente_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incidente no encontrado")

    logger.info(f"[backend] Recibida actualización de ubicación del técnico para incidente: {incidente_id} ({payload.latitud}, {payload.longitud})")
    from app.services.tracking_ws import tracking_ws_manager
    if inc.estado == "aceptada" and tracking_ws_manager.visual_states.get(inc.id) is None:
        tracking_ws_manager.visual_states[inc.id] = "en_camino"
        logger.info(f"[backend] Set visual state of incident {inc.id} to 'en_camino' upon receiving location update")
        
    updated = update_incidente_tecnico_ubicacion(db, inc, empleado, payload)
    tracking = get_incidente_tracking(db, inc)
    await tracking_ws_manager.broadcast(
        inc.id,
        {
            "event": "technician_location_updated",
            "tracking": tracking,
        },
    )
    logger.info(f"[backend] WebSocket broadcast realizado de ubicación para incidente: {inc.id}")

    return {
        "incidente_id": incidente_id,
        "empleado_id": updated.id,
        "latitud": float(updated.latitud_actual) if updated.latitud_actual is not None else None,
        "longitud": float(updated.longitud_actual) if updated.longitud_actual is not None else None,
        "disponible": updated.disponible,
        "ubicacion_actualizada_en": updated.ubicacion_actualizada_en.isoformat() if updated.ubicacion_actualizada_en else None,
    }


@router.get("/{incidente_id}/tracking", response_model=IncidenteTrackingOut)
def incidentes_tracking(incidente_id: str, user=Depends(get_current_user), db: Session = Depends(get_db)) -> IncidenteTrackingOut:
    try:
        inc = get_incidente_or_404(db, incidente_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incidente no encontrado")
    return get_incidente_tracking(db, inc)


@router.websocket("/{incidente_id}/ws/tracking")
async def incidentes_tracking_ws(websocket: WebSocket, incidente_id: str) -> None:
    await tracking_ws_manager.connect(incidente_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        tracking_ws_manager.disconnect(incidente_id, websocket)
    except Exception:
        tracking_ws_manager.disconnect(incidente_id, websocket)


# ============================================================
# ESTADO (Endpoint específico para móvil)
# ============================================================

@router.patch("/{incidente_id}/estado", response_model=dict)
async def incidentes_patch_estado(
    incidente_id: str,
    payload: IncidentePatchEstado,  # ← Usa un schema específico
    empleado=Depends(get_current_employee),
    db: Session = Depends(get_db)
) -> dict:
    """Actualizar solo el estado del incidente (útil para móvil)"""
    _estado_norm = (payload.estado or '').strip().lower()
    logger.info(f"[backend] iniciar recorrido clickeado / recibido estado: '{_estado_norm}' para incidente: {incidente_id}")
    try:
        inc = get_incidente_or_404(db, incidente_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incidente no encontrado")
    
    target_state = payload.estado
    estado_recibido = target_state
    
    # Nota: en_camino/en_sitio/en_proceso son etapas visuales, no estados persistidos
    mapeado = False
    if target_state in {"en_camino", "en_sitio", "en_proceso"}:
        target_state = "aceptada"
        mapeado = True
    elif target_state == "finalizado":
        target_state = "atendido"
        mapeado = True
        
    logger.info(f"[backend] incidentes_patch_estado: estado_recibido='{estado_recibido}', estado_guardado='{target_state}', mapeado={mapeado}")
    
    valid_states = {"pendiente", "aceptada", "asignada", "atendido", "completada", "cancelada"}
    if target_state in valid_states:
        inc.estado = target_state
    else:
        logger.warning(f"[backend] Intento de guardar estado invalido en BD: '{target_state}'")

    # Save visual state in memory
    from app.services.tracking_ws import tracking_ws_manager
    if _estado_norm in {"en_camino", "en_sitio"}:
        tracking_ws_manager.visual_states[incidente_id] = _estado_norm
        logger.info(f"[backend] Guardado estado visual temporal '{_estado_norm}' en memoria para incidente: {incidente_id}")
    elif _estado_norm in {"finalizado", "atendido", "finalizada"}:
        tracking_ws_manager.visual_states.pop(incidente_id, None)
        logger.info(f"[backend] Limpiado estado visual en memoria para incidente: {incidente_id}")

    # Sync active assignment estado_tarea with the incidente estado for key transitions
    _tarea_map = {
        'en_camino': 'aceptada',
        'en_sitio': 'aceptada',
        'en_proceso': 'aceptada',
        'atendido': 'finalizado',
        'finalizado': 'finalizado',
    }
    if _estado_norm in _tarea_map:
        try:
            _asign = get_active_asignacion_for_incidente(db, inc.id)
            if _asign and _asign.empleado_id == getattr(empleado, 'id', None):
                _asign.estado_tarea = _tarea_map[_estado_norm]
                db.add(_asign)
        except Exception:
            logger.exception("Error sincronizando estado_tarea para incidente %s", inc.id)

    # Si el empleado cambia a "en_camino" o "en_proceso", actualizar ubicación y notificar
    if _estado_norm in {'en_camino', 'en_proceso'}:
        # Actualizar ubicación del empleado si se proporciona
        if payload.latitud is not None and payload.longitud is not None:
            logger.info(f"[backend] backend recibió ubicación inicial: ({payload.latitud}, {payload.longitud}) para incidente: {incidente_id}")
            try:
                ubicacion_update = TecnicoUbicacionUpdate(
                    latitud=payload.latitud,
                    longitud=payload.longitud
                )
                update_tecnico_ubicacion(db, empleado, ubicacion_update)
            except Exception:
                pass

        # Notificar al cliente que el empleado está en camino
        try:
            from app.services.notification_service import notify_incidente_en_proceso, notify_incidente_iniciado
            notify_incidente_en_proceso(db, inc.id)
            try:
                notify_incidente_iniciado(db, inc.id, actor_empleado_id=getattr(empleado, 'id', None))
            except Exception:
                logger.exception("Error notificando inicio a administradores para incidente %s", inc.id)
        except Exception:
            pass

    db.commit()

    # Broadcast state change to administration WebSockets
    try:
        tracking = get_incidente_tracking(db, inc)
        await tracking_ws_manager.broadcast(
            inc.id,
            {
                "event": "technician_state_changed",
                "tracking": tracking,
            },
        )
        logger.info(f"[backend] WebSocket broadcast realizado por cambio de estado de incidente: {inc.id}")
    except Exception:
        logger.exception("Error retransmitiendo cambio de estado por WebSocket")

    # Regla de cancelación automática: si la solicitud es cancelada después de haberse aceptado,
    # el sistema penaliza con 1 estrella el promedio del taller.
    if (payload.estado or '').strip().lower() in {'cancelado', 'cancelada'}:
        try:
            asignacion = get_active_asignacion_for_incidente(db, inc.id)
            if asignacion and asignacion.empresa_id:
                register_sistema_rating_for_empresa(db, asignacion.empresa_id, 1)
                asignacion.estado_tarea = 'cancelado'
                db.add(asignacion)
                db.commit()
        except Exception:
            logger.exception("Error actualizando reputación del taller tras cancelación de la solicitud")

    # If the incident was marked as attended, notify admins and client
    try:
        if (payload.estado or '').strip().lower() == 'atendido':
            close_active_asignacion_for_incidente(db, inc.id)
            from app.services.notification_service import notify_incidente_atendido
            # pass the empleado id who requested the change so admins get the actor name
            notify_incidente_atendido(db, inc.id, actor_empleado_id=getattr(empleado, 'id', None))
    except Exception:
        # do not fail the request if notifications error
        pass

    return {"id": inc.id, "estado": inc.estado}


# ============================================================
# DIAGNÓSTICO
# ============================================================

@router.post("/{incidente_id}/diagnosticos", response_model=dict)
def incidentes_add_diagnostico(
    incidente_id: str,
    body: dict,
    user = Depends(require_permission("manage_incidentes")),
    db: Session = Depends(get_db)
) -> dict:
    """Agregar diagnóstico a un incidente"""
    try:
        inc = get_incidente_or_404(db, incidente_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incidente no encontrado")
    
    diag = add_diagnostico(
        db, inc,
        clasificacion=body.get("clasificacion"),
        resumen=body.get("resumen"),
        prioridad=body.get("prioridad")
    )
    return {"id": diag.id, "message": "Diagnóstico agregado"}


@router.get("/{incidente_id}/diagnosticos", response_model=list)
def incidentes_get_diagnosticos(
    incidente_id: str,
    db: Session = Depends(get_db)
) -> list:
    """Obtener diagnóstico(s) de un incidente"""
    try:
        _ = get_incidente_or_404(db, incidente_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incidente no encontrado")
    
    diagnosticos = list_diagnosticos_for_incidente(db, incidente_id)
    return [
        {
            "id": d.id,
            "clasificacion": d.clasificacion,
            "resumen": d.resumen,
            "prioridad": d.prioridad
        }
        for d in diagnosticos
    ]


@router.put("/diagnosticos/{diagnostico_id}", response_model=dict)
def incidentes_put_diagnostico(
    diagnostico_id: str,
    body: dict,
    user = Depends(require_permission("manage_incidentes")),
    db: Session = Depends(get_db)
) -> dict:
    """Actualizar un diagnóstico existente"""
    try:
        diag = get_diagnostico_or_404(db, diagnostico_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Diagnóstico no encontrado")
    
    updated = update_diagnostico(
        db, diag,
        clasificacion=body.get("clasificacion"),
        resumen=body.get("resumen"),
        prioridad=body.get("prioridad")
    )
    return {"id": updated.id, "message": "Diagnóstico actualizado"}


# ============================================================
# EVIDENCIAS
# ============================================================

@router.post("/{incidente_id}/evidencias", response_model=dict)
def incidentes_add_evidencia(
    incidente_id: str,
    body: dict,
    current_user = Depends(get_current_user),  # Cliente puede subir evidencias
    db: Session = Depends(get_db)
) -> dict:
    """Agregar evidencia a un incidente (foto, texto, etc.)"""
    try:
        inc = get_incidente_or_404(db, incidente_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incidente no encontrado")
    ev = add_evidencia(
        db,
        inc,
        body.get("tipo", "texto"),
        url_archivo=body.get("url_archivo"),
        texto=body.get("texto"),
    )
    return {"id": ev.id}


@router.post("/{incidente_id}/evidencias/upload", response_model=dict)
def incidentes_add_evid_file(
    incidente_id: str,
    request: Request,
    archivo: UploadFile = File(...),
    tipo: str | None = Form(default=None),
    texto: str | None = Form(default=None),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    try:
        inc = get_incidente_or_404(db, incidente_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incidente no encontrado")

    inferred_tipo = tipo
    content_type = (archivo.content_type or "").lower()
    if not inferred_tipo:
        if content_type.startswith("image/"):
            inferred_tipo = "foto"
        elif content_type.startswith("audio/"):
            inferred_tipo = "audio"
        else:
            inferred_tipo = "archivo"

    # save to temp file
    tmp_dir = tempfile.mkdtemp(prefix="evidence_")
    tmp_path = os.path.join(tmp_dir, archivo.filename or "upload.bin")
    try:
        with open(tmp_path, "wb") as out:
            out.write(archivo.file.read())

        # Try Cloudinary first; if it is not configured or fails, store locally.
        use_cloudinary = all(
            [
                settings.cloudinary_cloud_name,
                settings.cloudinary_api_key,
                settings.cloudinary_api_secret,
            ]
        )

        try:
            if use_cloudinary:
                folder = f"incidentes/{inc.id}"
                public_url = cloudinary_upload_evidence(tmp_path, folder=folder)
            else:
                archivo.file.seek(0)
                rel_path = save_incidente_evidence(archivo, inc.id)
                public_url = str(request.base_url).rstrip("/") + f"{settings.media_url}/{rel_path}"
        except Exception as exc:
            try:
                archivo.file.seek(0)
                rel_path = save_incidente_evidence(archivo, inc.id)
                public_url = str(request.base_url).rstrip("/") + f"{settings.media_url}/{rel_path}"
            except Exception as local_exc:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Error subiendo evidencia: {exc}; fallback local falló: {local_exc}",
                )

        final_text = texto or ""

        # If audio, transcribe
        is_audio = inferred_tipo == "audio" or content_type.startswith("audio/")
        if is_audio:
            try:
                transcription = transcribe_audio(tmp_path)
            except Exception as exc:
                raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Error transcribiendo audio: {exc}")
            if transcription:
                if final_text:
                    final_text = f"{final_text}\n{transcription}"
                else:
                    final_text = transcription

        # persist evidencia
        ev = add_evidencia(db, inc, inferred_tipo, url_archivo=public_url, texto=final_text)

    finally:
        try:
            shutil.rmtree(tmp_dir)
        except Exception:
            pass

    return {"id": ev.id, "url_archivo": public_url, "tipo": inferred_tipo, "texto": ev.texto}


# ============================================================
# FASE 1 — Asignación de Talleres
# ============================================================

@router.get("/talleres/cercanos", response_model=list[TallerCercanoOut])
def talleres_cercanos(
    latitud: float = Query(..., ge=-90, le=90),
    longitud: float = Query(..., ge=-180, le=180),
    radio_km: float = Query(default=5.0, gt=0, le=50),
    servicio: str | None = Query(default=None, description="Filtrar por tipo de servicio (ej: grua, mecanica)"),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[TallerCercanoOut]:
    """Buscar talleres cercanos al punto indicado.

    Criterios de asignación:
    - 3.1  Talleres dentro del radio (default 5 km).
    - 3.2  Talleres que ofrecen el servicio solicitado.
    - 3.4  Ordenados por puntuación alta.
    """
    return find_talleres_cercanos(
        db,
        latitud=latitud,
        longitud=longitud,
        radio_km=radio_km,
        servicio_tipo=servicio,
    )


@router.post("/{incidente_id}/auto-asignar", response_model=AutoAsignarResponse)
def incidentes_auto_asignar(
    incidente_id: str,
    radio_km: float = Query(default=5.0, gt=0, le=50),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AutoAsignarResponse:
    """Busca el mejor taller para el incidente y lo acepta automáticamente.

    Criterios: radio 5 km, servicio coincidente, mayor puntuación.
    Si se encuentra un taller, el incidente pasa a estado 'aceptada' con
    ``accepted_empresa_id`` asignado y se registra gamificación (+5).
    """
    try:
        inc = get_incidente_or_404(db, incidente_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incidente no encontrado")

    talleres = find_talleres_cercanos(
        db,
        latitud=float(inc.latitud) if inc.latitud else 0,
        longitud=float(inc.longitud) if inc.longitud else 0,
        radio_km=radio_km,
        servicio_tipo=inc.tipo,
    )

    taller_asignado = auto_asignar_taller(db, inc, radio_km=radio_km)

    return AutoAsignarResponse(
        incidente_id=incidente_id,
        talleres_encontrados=len(talleres),
        taller_asignado=taller_asignado,
        talleres=talleres,
    )
