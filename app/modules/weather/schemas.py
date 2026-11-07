from pydantic import BaseModel


class ClimaOut(BaseModel):
    """Clima que muestra la pantalla de Inicio."""

    ciudad: str = "Lima Metropolitana"
    temperatura: float
    humedad: float
    viento_kmh: float
    observado: str