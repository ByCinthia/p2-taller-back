"""Router de Reportes Dinámicos con IA Local (Fase 4).

Genera reportes en texto o PDF usando un modelo de IA local (Ollama).
Soporta entrada por texto libre y por audio (transcripción automática).
"""
from __future__ import annotations

import logging
import os
import shutil
import tempfile

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

import io

from app.core.config import get_settings
from app.core.tenant import TenantContext, get_tenant
from app.db.session import get_db
from app.schemas.reporte_schema import ReporteRequest, ReporteResponse
from app.services.ai_report_service import generate_report_pdf, generate_report_text
from app.services.transcription_service import transcribe_audio

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/reportes", tags=["reportes"])


def _resolve_empresa_id(tenant: TenantContext, empresa_id_query: str | None) -> str | None:
    if tenant.empleado and not tenant.user.is_staff:
        return tenant.empresa_id
    return empresa_id_query


# ============================================================
# Reporte por texto
# ============================================================

@router.post("/generar", response_model=ReporteResponse)
def generar_reporte(
    payload: ReporteRequest,
    tenant: TenantContext = Depends(get_tenant),
    db: Session = Depends(get_db),
) -> ReporteResponse | StreamingResponse:
    """Genera un reporte dinámico usando IA local (Ollama).

    - ``formato=texto``: devuelve JSON con el reporte en texto.
    - ``formato=pdf``: devuelve archivo PDF para descarga.
    """
    eid = _resolve_empresa_id(tenant, payload.empresa_id)

    if payload.formato == "pdf":
        pdf_bytes = generate_report_pdf(db, payload.prompt, empresa_id=eid)
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=reporte.pdf"},
        )

    resultado = generate_report_text(db, payload.prompt, empresa_id=eid)
    return ReporteResponse(
        reporte=resultado["reporte"],
        metadata=resultado["metadata"],
        datos_contexto=resultado["datos_contexto"],
    )


# ============================================================
# Reporte por audio
# ============================================================

@router.post("/generar-audio")
def generar_reporte_audio(
    archivo: UploadFile = File(...),
    formato: str = Form(default="texto"),
    empresa_id: str | None = Form(default=None),
    tenant: TenantContext = Depends(get_tenant),
    db: Session = Depends(get_db),
):
    """Genera un reporte a partir de un archivo de audio.

    El audio se transcribe automáticamente usando OpenAI Whisper
    y luego se pasa al modelo de IA local para generar el reporte.
    """
    content_type = (archivo.content_type or "").lower()
    if not content_type.startswith("audio/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo debe ser de tipo audio",
        )

    # Guardar temporalmente
    tmp_dir = tempfile.mkdtemp(prefix="report_audio_")
    tmp_path = os.path.join(tmp_dir, archivo.filename or "audio.bin")
    try:
        with open(tmp_path, "wb") as out:
            out.write(archivo.file.read())

        # Transcribir
        try:
            transcripcion = transcribe_audio(tmp_path)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Error transcribiendo audio: {exc}",
            )

        if not transcripcion:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se pudo obtener transcripción del audio",
            )

        eid = _resolve_empresa_id(tenant, empresa_id)

        if formato == "pdf":
            pdf_bytes = generate_report_pdf(db, transcripcion, empresa_id=eid)
            return StreamingResponse(
                io.BytesIO(pdf_bytes),
                media_type="application/pdf",
                headers={"Content-Disposition": "attachment; filename=reporte_audio.pdf"},
            )

        resultado = generate_report_text(db, transcripcion, empresa_id=eid)
        return ReporteResponse(
            reporte=resultado["reporte"],
            metadata={**resultado["metadata"], "transcripcion": transcripcion},
            datos_contexto=resultado["datos_contexto"],
        )

    finally:
        try:
            shutil.rmtree(tmp_dir)
        except Exception:
            pass


# ============================================================
# Estado de Ollama
# ============================================================

@router.get("/estado-ia")
def estado_ia():
    """Verifica si el servicio de IA local (Ollama) está disponible."""
    from app.services.ai_report_service import _check_ollama_available, _get_ollama_client

    settings = get_settings()
    disponible = _check_ollama_available()

    modelos = []
    if disponible:
        try:
            client = _get_ollama_client()
            resp = client.list()
            modelos = [m.model for m in resp.models] if hasattr(resp, "models") else []
        except Exception:
            pass

    return {
        "ollama_disponible": disponible,
        "url": settings.ollama_base_url,
        "modelo_configurado": settings.ollama_model,
        "modelos_instalados": modelos,
    }
