from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db.models import Empresa


def _calculate_moving_average(current_average: Decimal, total_ratings: int, new_rating: int) -> Decimal:
    """Calcula el promedio móvil con precisión de 2 decimales."""
    if total_ratings < 0:
        total_ratings = 0

    numerator = (current_average * Decimal(total_ratings)) + Decimal(new_rating)
    denominator = Decimal(total_ratings + 1)
    new_average = numerator / denominator
    return new_average.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def register_sistema_rating_for_empresa(db: Session, empresa_id: str, rating: int) -> Empresa:
    """Registra una calificación automática del usuario virtual 'SISTEMA'."""
    if rating < 1 or rating > 5:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="La calificación debe estar entre 1 y 5 estrellas")

    empresa = db.get(Empresa, empresa_id)
    if not empresa:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empresa no encontrada para evaluación")

    current_average = Decimal(str(empresa.estrellas_promedio or Decimal("5.00")))
    current_total = int(empresa.total_calificaciones or 0)
    # calculate new average (already quantized to 2 decimals)
    new_avg = _calculate_moving_average(current_average, current_total, rating)
    empresa.estrellas_promedio = new_avg
    empresa.total_calificaciones = current_total + 1

    db.add(empresa)
    db.commit()
    db.refresh(empresa)
    return empresa


__all__ = [
    "register_sistema_rating_for_empresa",
]
