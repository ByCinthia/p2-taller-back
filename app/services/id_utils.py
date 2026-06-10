import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session


def get_next_numeric_id(db: Session, model) -> str:
    """Devuelve el siguiente id numérico como cadena para la tabla del modelo.

    Intenta obtener todos los valores de `id` y si encuentra IDs numéricos
    devuelve el siguiente número secuencial como cadena. Si ocurre algún
    error o no hay IDs numéricos, genera un UUID como fallback.
    """
    try:
        rows = db.execute(select(model.id)).scalars().all()
        numeric_ids = []
        for x in rows:
            if x is None:
                continue
            s = str(x)
            if s.isdigit():
                numeric_ids.append(int(s))
        next_id = str((max(numeric_ids) + 1) if numeric_ids else 1)
    except Exception:
        next_id = str(uuid.uuid4())
    return next_id
