from decimal import Decimal
from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import ORMModel


class PagoCreate(BaseModel):
    monto_total: Decimal | None = None
    metodo_pago: str  # 'efectivo', 'qr_simulado', 'tarjeta_simulada'


class PagoOut(ORMModel):
    id: str
    asignacion_id: str
    incidente_id: str | None
    cliente_id: str | None
    empresa_id: str | None
    monto_total: Decimal
    metodo_pago: str
    estado: str
    comision_plataforma: Decimal | None
    monto_taller: Decimal | None
    fecha_creacion: datetime
    fecha_confirmacion: datetime | None
