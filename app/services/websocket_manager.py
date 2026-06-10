from fastapi import WebSocket
from typing import Dict, Set
import logging

logger = logging.getLogger(__name__)

class ConnectionManager:
    """
    Gestiona las conexiones activas de WebSockets para clientes y técnicos.
    Almacena las conexiones organizadas por el ID del incidente para retransmitir
    las coordenadas del técnico únicamente a los clientes que observan dicho incidente.
    """
    def __init__(self):
        # Mapea incidente_id (str) -> conjunto de conexiones WebSocket de clientes
        self.client_connections: Dict[str, Set[WebSocket]] = {}
        # Mapea incidente_id (str) -> conexión WebSocket única del técnico asignado
        self.technician_connections: Dict[str, WebSocket] = {}

    async def connect_client(self, incident_id: str, websocket: WebSocket) -> None:
        """Acepta la conexión de un cliente interesado en seguir el incidente."""
        await websocket.accept()
        if incident_id not in self.client_connections:
            self.client_connections[incident_id] = set()
        self.client_connections[incident_id].add(websocket)
        logger.info(
            f"Cliente conectado al tracking del incidente: {incident_id}. "
            f"Total clientes: {len(self.client_connections[incident_id])}"
        )

    def disconnect_client(self, incident_id: str, websocket: WebSocket) -> None:
        """Remueve al cliente de la lista de receptores del tracking."""
        if incident_id in self.client_connections:
            self.client_connections[incident_id].discard(websocket)
            if not self.client_connections[incident_id]:
                del self.client_connections[incident_id]
        logger.info(f"Cliente desconectado del tracking del incidente: {incident_id}")

    async def connect_technician(self, incident_id: str, websocket: WebSocket) -> None:
        """Acepta la conexión del técnico que emitirá su ubicación."""
        await websocket.accept()
        # Si ya existe un socket activo para este técnico, se cierra cordialmente
        if incident_id in self.technician_connections:
            try:
                await self.technician_connections[incident_id].close(
                    code=1000, 
                    reason="Nueva conexion establecida para este tecnico"
                )
            except Exception:
                pass
        self.technician_connections[incident_id] = websocket
        logger.info(f"Técnico conectado para emitir en incidente: {incident_id}")

    def disconnect_technician(self, incident_id: str, websocket: WebSocket) -> None:
        """Desconecta al técnico y limpia su conexión si coincide con la almacenada."""
        if incident_id in self.technician_connections:
            if self.technician_connections[incident_id] == websocket:
                del self.technician_connections[incident_id]
        logger.info(f"Técnico desconectado del incidente: {incident_id}")

    async def broadcast_to_clients(self, incident_id: str, message: dict) -> None:
        """Envía las coordenadas actualizadas a todos los clientes suscritos al incidente."""
        if incident_id in self.client_connections:
            disconnected_sockets = set()
            for connection in list(self.client_connections[incident_id]):
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error enviando tracking a cliente en incidente {incident_id}: {e}")
                    disconnected_sockets.add(connection)
            for ws in disconnected_sockets:
                self.disconnect_client(incident_id, ws)

# Instancia global única para toda la aplicación
tracking_ws_manager = ConnectionManager()


class NotificationConnectionManager:
    """
    Gestiona las conexiones WebSocket activas para el envío de notificaciones en tiempo real.
    Permite enviar alertas personalizadas a usuarios específicos.
    """
    def __init__(self):
        # Mapea user_id (str) -> conjunto de conexiones WebSocket del usuario
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, user_id: str, websocket: WebSocket) -> None:
        """Acepta la conexión WebSocket de un usuario para notificaciones."""
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)
        logger.info(f"Usuario {user_id} conectado para recibir notificaciones en tiempo real.")

    def disconnect(self, user_id: str, websocket: WebSocket) -> None:
        """Remueve la conexión activa del usuario."""
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        logger.info(f"Usuario {user_id} desconectado del servicio de notificaciones.")

    async def send_to_user(self, user_id: str, message: dict) -> None:
        """Envía una notificación en formato JSON a todas las conexiones activas de un usuario."""
        if user_id in self.active_connections:
            disconnected_sockets = set()
            for connection in list(self.active_connections[user_id]):
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error enviando notificación a usuario {user_id}: {e}")
                    disconnected_sockets.add(connection)
            for ws in disconnected_sockets:
                self.disconnect(user_id, ws)


notification_ws_manager = NotificationConnectionManager()

