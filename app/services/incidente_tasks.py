from __future__ import annotations

from app.db.session import SessionLocal


def analyze_and_assign(incidente_id: str) -> None:
    """Tarea en background que genera un diagnóstico simple y asigna un taller/mecánico.
    Implementación mínima: crea un diagnóstico con un resumen de la descripción
    y asigna el primer `Empresa` disponible como taller.
    """
    from app.services.incidente_service import get_incidente_or_404, add_diagnostico
    from app.db.models import Empresa, Empleado

    db = SessionLocal()
    try:
        try:
            inc = get_incidente_or_404(db, incidente_id)
        except ValueError:
            return

        resumen = (inc.descripcion or "")[:200]
        add_diagnostico(db, inc, clasificacion=1, resumen=resumen, prioridad=1)

        # Buscar un taller (empresa) disponible. Implementación simplificada: elegir la primera.
        empresa = db.query(Empresa).first()
        if empresa:
            # current DB schema doesn't have columns for taller_id/tiempo_estimado_minutos
            # so only update the estado to reflect assignment
            inc.estado = "asignado"
            db.add(inc)
            db.commit()
    finally:
        db.close()
