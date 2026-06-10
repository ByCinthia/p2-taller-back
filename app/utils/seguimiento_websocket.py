from __future__ import annotations

from collections import defaultdict

from fastapi import WebSocket


class TrackingConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = defaultdict(set)

    async def connect(self, incidente_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections[incidente_id].add(websocket)

    def disconnect(self, incidente_id: str, websocket: WebSocket) -> None:
        conexiones = self._connections.get(incidente_id)
        if not conexiones:
            return

        conexiones.discard(websocket)
        if not conexiones:
            self._connections.pop(incidente_id, None)

    async def broadcast(self, incidente_id: str, payload: dict) -> None:
        conexiones = self._connections.get(incidente_id)
        if not conexiones:
            return

        to_remove: list[WebSocket] = []
        for ws in list(conexiones):
            try:
                await ws.send_json(payload)
            except Exception:
                to_remove.append(ws)

        for ws in to_remove:
            self.disconnect(incidente_id, ws)


tracking_ws_manager = TrackingConnectionManager()
