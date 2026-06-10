from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from pydantic import ValidationError
from app.services.websocket_manager import tracking_ws_manager, notification_ws_manager
from app.schemas.tracking import TrackingSchema
import json
import logging

logger = logging.getLogger(__name__)

# Prefijo dedicado a los WebSockets de rastreo
router = APIRouter(prefix="/ws/tracking", tags=["websocket-tracking"])

@router.websocket("/notifications/{user_id}")
async def notifications_websocket(websocket: WebSocket, user_id: str) -> None:
    """
    Endpoint WebSocket para recibir notificaciones de sistema en tiempo real.
    """
    await notification_ws_manager.connect(user_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        notification_ws_manager.disconnect(user_id, websocket)
    except Exception as e:
        logger.error(f"Error en socket de notificaciones para usuario {user_id}: {e}")
        notification_ws_manager.disconnect(user_id, websocket)


@router.websocket("/{incidente_id}/{role}")
async def tracking_websocket(websocket: WebSocket, incidente_id: str, role: str) -> None:
    """
    Endpoint WebSocket para rastreo en tiempo real.
    El parámetro 'role' puede ser: 'client'/'cliente' o 'technician'/'tecnico'.
    """
    normalized_role = role.lower()
    
    if normalized_role in ["client", "cliente"]:
        # Conectar al cliente interesado en recibir la ubicación
        await tracking_ws_manager.connect_client(incidente_id, websocket)
        try:
            while True:
                data = await websocket.receive_text()
                if data == "ping":
                    await websocket.send_text("pong")
        except WebSocketDisconnect:
            tracking_ws_manager.disconnect_client(incidente_id, websocket)
        except Exception as e:
            logger.error(f"Error en socket de cliente para incidente {incidente_id}: {e}")
            tracking_ws_manager.disconnect_client(incidente_id, websocket)

    elif normalized_role in ["technician", "tecnico"]:
        # Conectar al técnico emisor de coordenadas
        await tracking_ws_manager.connect_technician(incidente_id, websocket)
        try:
            while True:
                data = await websocket.receive_text()
                if data == "ping":
                    await websocket.send_text("pong")
                    continue
                
                try:
                    payload = json.loads(data)
                    # Asegurar la presencia del incidente_id
                    if "incidente_id" not in payload:
                        payload["incidente_id"] = incidente_id
                    
                    # Validar coordenadas usando el esquema Pydantic
                    validated_data = TrackingSchema(**payload)
                    
                    # Estructurar mensaje a retransmitir (broadcast)
                    broadcast_message = {
                        "event": "location_update",
                        "incidente_id": validated_data.incidente_id,
                        "latitud": validated_data.latitud,
                        "longitud": validated_data.longitud
                    }
                    
                    # Broadcast a todos los clientes observando este incidente
                    await tracking_ws_manager.broadcast_to_clients(incidente_id, broadcast_message)
                except (json.JSONDecodeError, ValidationError) as err:
                    # Reportar error de formato al emisor
                    await websocket.send_json({
                        "error": "Formato de datos no valido",
                        "detail": str(err)
                    })
        except WebSocketDisconnect:
            tracking_ws_manager.disconnect_technician(incidente_id, websocket)
        except Exception as e:
            logger.error(f"Error en socket de tecnico para incidente {incidente_id}: {e}")
            tracking_ws_manager.disconnect_technician(incidente_id, websocket)
            
    else:
        # Si el rol es desconocido, se cierra la conexión
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION, 
            reason="Rol no permitido. Debe ser 'client' o 'technician'"
        )


