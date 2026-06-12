"""Servicio de Reportes Dinámicos con IA Local (Fase 4).

Usa Ollama (modelo local) para generar reportes en texto natural
a partir de datos estructurados del sistema.  Soporta entrada por
texto y audio (transcripción previa).  Genera salida en texto o PDF.

Requisitos:
- Ollama instalado y corriendo en el servidor (``ollama serve``)
- Modelo descargado: ``ollama pull llama3.2:3b``
"""
from __future__ import annotations

import io
import json
import logging
from datetime import datetime, timezone
from typing import Any

import ollama
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.lib import colors

from app.core.config import get_settings
from app.services.metricas_service import get_dashboard_metrics
from app.services.dashboard_service import get_resumen, get_incidentes_por_estado

logger = logging.getLogger(__name__)


# ============================================================
# Cliente Ollama
# ============================================================

def _get_ollama_client() -> ollama.Client:
    settings = get_settings()
    return ollama.Client(host=settings.ollama_base_url)


def _check_ollama_available() -> bool:
    """Verifica si Ollama está disponible."""
    try:
        client = _get_ollama_client()
        client.list()
        return True
    except Exception:
        logger.warning("Ollama no disponible en %s", get_settings().ollama_base_url)
        return False


# ============================================================
# Prompt engineering
# ============================================================

SYSTEM_PROMPT = """\
Eres un analista de datos especializado en servicios de auxilio mecánico.
Tu tarea es generar reportes claros, profesionales y accionables en español.

Reglas:
- Usa lenguaje formal pero accesible.
- Incluye cifras concretas cuando estén disponibles.
- Destaca tendencias, anomalías y recomendaciones.
- Estructura el reporte con secciones claras.
- Si no hay datos suficientes, indícalo honestamente.
- Máximo 800 palabras.
"""


def _build_context_text(datos: dict[str, Any]) -> str:
    """Convierte los datos del dashboard en texto legible para el modelo."""
    lines = []

    resumen = datos.get("resumen", {})
    if resumen:
        lines.append("=== RESUMEN GENERAL ===")
        lines.append(f"Total incidentes: {resumen.get('total_incidentes', 0)}")
        lines.append(f"Pendientes: {resumen.get('incidentes_pendientes', 0)}")
        lines.append(f"Aceptados: {resumen.get('incidentes_aceptados', 0)}")
        lines.append(f"Asignados: {resumen.get('incidentes_asignados', 0)}")
        lines.append(f"Atendidos: {resumen.get('incidentes_atendidos', 0)}")
        lines.append(f"Completados: {resumen.get('incidentes_completados', 0)}")
        lines.append(f"Cancelados: {resumen.get('incidentes_cancelados', 0)}")
        lines.append(f"Total talleres: {resumen.get('total_talleres', 0)}")
        lines.append(f"Total clientes: {resumen.get('total_clientes', 0)}")
        lines.append(f"Promedio estrellas talleres: {resumen.get('promedio_estrellas_talleres', 0)}")

    metricas = datos.get("metricas", {})
    if metricas:
        ta = metricas.get("tiempo_promedio_asignacion", {})
        tl = metricas.get("tiempo_promedio_llegada", {})
        lines.append("\n=== MÉTRICAS KPI ===")
        lines.append(f"Tiempo promedio asignación: {ta.get('minutos', 'N/A')} min ({ta.get('total_registros', 0)} registros)")
        lines.append(f"Tiempo promedio llegada: {tl.get('minutos', 'N/A')} min ({tl.get('total_registros', 0)} registros)")

        cancelados = metricas.get("casos_cancelados", {})
        lines.append(f"Cancelados total: {cancelados.get('total_cancelados', 0)} ({cancelados.get('porcentaje_cancelacion', 0)}%)")

        en_tiempo = metricas.get("solicitudes_en_tiempo", {})
        lines.append(f"Atendidas en tiempo: {en_tiempo.get('porcentaje', 0)}% ({en_tiempo.get('atendidas_en_tiempo', 0)}/{en_tiempo.get('total_asignadas', 0)})")

        tipos = metricas.get("tipos_incidentes", [])
        if tipos:
            lines.append("\n=== TIPOS DE INCIDENTES ===")
            for t in tipos[:10]:
                lines.append(f"- {t.get('tipo', 'Sin tipo')}: {t.get('cantidad', 0)}")

        talleres = metricas.get("talleres_eficientes", [])
        if talleres:
            lines.append("\n=== TOP TALLERES ===")
            for t in talleres[:5]:
                lines.append(
                    f"- {t.get('nombre', '?')}: eficiencia={t.get('puntuacion_eficiencia', 0):.2f}, "
                    f"estrellas={t.get('estrellas_promedio', 0):.1f}, "
                    f"incidentes={t.get('total_incidentes', 0)}"
                )

    return "\n".join(lines)


# ============================================================
# Generación de reporte con IA
# ============================================================

def generate_report_text(
    db,
    prompt_usuario: str,
    empresa_id: str | None = None,
) -> dict[str, Any]:
    """Genera un reporte en texto usando Ollama + datos del sistema.

    Args:
        db: Sesión de base de datos.
        prompt_usuario: Instrucción del usuario (texto o transcripción de audio).
        empresa_id: Filtro opcional por taller.

    Returns:
        Dict con ``reporte`` (texto generado), ``datos_contexto`` y ``metadata``.
    """
    # 1. Recopilar datos del sistema
    resumen = get_resumen(db, empresa_id=empresa_id)
    metricas = get_dashboard_metrics(db, empresa_id=empresa_id)

    datos = {
        "resumen": resumen.model_dump(),
        "metricas": metricas.model_dump(),
    }

    contexto = _build_context_text(datos)

    # 2. Construir prompt completo
    user_prompt = f"""\
DATOS DEL SISTEMA:
{contexto}

SOLICITUD DEL USUARIO:
{prompt_usuario}

Genera un reporte profesional basado en los datos anteriores y la solicitud del usuario.\
"""

    # 3. Llamar a Ollama
    settings = get_settings()
    model = settings.ollama_model

    try:
        client = _get_ollama_client()
        response = client.chat(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            options={"temperature": 0.4, "num_predict": 1500},
        )
        reporte_texto = response.message.content.strip()
    except Exception as exc:
        logger.exception("Error generando reporte con Ollama")
        reporte_texto = (
            f"[Error] No se pudo generar el reporte con IA local. "
            f"Verifica que Ollama esté corriendo en {settings.ollama_base_url} "
            f"y que el modelo '{model}' esté descargado.\n\n"
            f"Error técnico: {exc}"
        )

    return {
        "reporte": reporte_texto,
        "datos_contexto": datos,
        "metadata": {
            "modelo": model,
            "generado_en": datetime.now(timezone.utc).isoformat(),
            "empresa_id": empresa_id,
            "prompt_original": prompt_usuario,
        },
    }


# ============================================================
# Generación de PDF
# ============================================================

def generate_report_pdf(
    db,
    prompt_usuario: str,
    empresa_id: str | None = None,
) -> bytes:
    """Genera un reporte en PDF combinando texto de IA + tablas de datos."""
    resultado = generate_report_text(db, prompt_usuario, empresa_id)
    reporte_texto = resultado["reporte"]
    datos = resultado["datos_contexto"]

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "CustomTitle", parent=styles["Heading1"], fontSize=18, spaceAfter=20
    )
    subtitle_style = ParagraphStyle(
        "Subtitle", parent=styles["Heading2"], fontSize=12, spaceAfter=10
    )
    body_style = ParagraphStyle(
        "Body", parent=styles["Normal"], fontSize=10, leading=14, spaceAfter=8
    )

    elements = []

    # Título
    elements.append(Paragraph("Reporte Dinámico - Auxilio Mecánico", title_style))
    elements.append(
        Paragraph(
            f"Generado: {resultado['metadata']['generado_en']} | Modelo: {resultado['metadata']['modelo']}",
            subtitle_style,
        )
    )
    elements.append(Spacer(1, 0.5 * cm))

    # Texto del reporte IA (dividir por párrafos)
    for parrafo in reporte_texto.split("\n\n"):
        parrafo = parrafo.strip()
        if parrafo:
            # Detectar encabezados simples
            if parrafo.startswith("#"):
                elements.append(Paragraph(parrafo.lstrip("#").strip(), subtitle_style))
            else:
                elements.append(Paragraph(parrafo.replace("\n", "<br/>"), body_style))

    elements.append(Spacer(1, 1 * cm))

    # Tabla de resumen
    resumen = datos.get("resumen", {})
    if resumen:
        elements.append(Paragraph("Resumen Numérico", subtitle_style))
        table_data = [
            ["Métrica", "Valor"],
            ["Total Incidentes", str(resumen.get("total_incidentes", 0))],
            ["Pendientes", str(resumen.get("incidentes_pendientes", 0))],
            ["Atendidos", str(resumen.get("incidentes_atendidos", 0))],
            ["Completados", str(resumen.get("incidentes_completados", 0))],
            ["Cancelados", str(resumen.get("incidentes_cancelados", 0))],
            ["Talleres", str(resumen.get("total_talleres", 0))],
            ["Clientes", str(resumen.get("total_clientes", 0))],
            ["Estrellas Promedio", str(resumen.get("promedio_estrellas_talleres", 0))],
        ]
        table = Table(table_data, colWidths=[8 * cm, 6 * cm])
        table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#ecf0f1")]),
            ])
        )
        elements.append(table)

    doc.build(elements)
    buffer.seek(0)
    return buffer.read()
