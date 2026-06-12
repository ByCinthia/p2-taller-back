"""Schemas para Reportes Dinámicos con IA (Fase 4)."""
from __future__ import annotations

from pydantic import BaseModel


class ReporteRequest(BaseModel):
    """Solicitud de generación de reporte por texto."""
    prompt: str
    formato: str = "texto"  # texto | pdf
    empresa_id: str | None = None


class ReporteResponse(BaseModel):
    """Respuesta de reporte generado en texto."""
    reporte: str
    metadata: dict
    datos_contexto: dict | None = None


class ReporteAudioRequest(BaseModel):
    """Metadata para reporte generado desde audio (el archivo se sube como multipart)."""
    formato: str = "texto"  # texto | pdf
    empresa_id: str | None = None
