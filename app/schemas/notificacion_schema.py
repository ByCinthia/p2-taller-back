from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class NotificacionOut(BaseModel):
    id: str
    titulo: str
    mensaje: str
    tipo: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    leida: bool
    leida_en: datetime | None = None
    creada_en: datetime


class NotificacionListOut(BaseModel):
    items: list[NotificacionOut]
    total: int
