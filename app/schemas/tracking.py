from pydantic import BaseModel, Field

class TrackingSchema(BaseModel):
    """
    Esquema de validación para las coordenadas enviadas por el técnico
    durante el rastreo de ubicación en tiempo real.
    """
    latitud: float = Field(..., ge=-90, le=90, description="Latitud de la ubicación actual del técnico")
    longitud: float = Field(..., ge=-180, le=180, description="Longitud de la ubicación actual del técnico")
    incidente_id: str = Field(..., description="ID del incidente asociado al cual se reporta ubicación")
