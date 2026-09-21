from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

Ubicacion = Literal[
    "Balcon", "Ventana", "Terraza", "Patio", "Interior", "Jardin"
]
Etapa = Literal[
    "Germinacion", "Crecimiento", "Floracion", "Fructificacion", "Cosecha"
]
EstadoPlanta = Literal["Sin_diagnostico", "Sana", "En_tratamiento"]


class PlantaCreate(BaseModel):
    apodo: str = Field(min_length=1, max_length=60)
    ubicacion: Ubicacion
    etapa: Etapa = "Crecimiento"
    species_id: str | None = None
    fecha_siembra: date | None = None
    ultimo_riego: date | None = None


class PlantaUpdate(BaseModel):
    apodo: str | None = Field(default=None, min_length=1, max_length=60)
    ubicacion: Ubicacion | None = None
    etapa: Etapa | None = None
    species_id: str | None = None
    fecha_siembra: date | None = None
    ultimo_riego: date | None = None


class PlantaResumen(BaseModel):
    id: str
    apodo: str
    especie: str | None = None
    ubicacion: str
    etapa: str
    estado: str
    foto_url: str | None = None
    riego_frecuencia_dias: int | None = None
    ultimo_riego: date | None = None
    proximo_riego: date | None = None
    dias_para_riego: int | None = None
    proximo_tratamiento: date | None = None
    dias_para_tratamiento: int | None = None
    proximo_tipo: str | None = None  # <--- Este campo es obligatorio


class DiagnosticoResumen(BaseModel):
    # Entrada del historial de diagnósticos de una planta.
    id: str
    nombre_enfermedad: str | None
    estado: str
    confianza: float
    imagen_url: str
    created_at: datetime


class PlantaDetalle(PlantaResumen):
    # Vista completa de una planta con su historial.
    species_id: str | None
    fecha_siembra: date | None
    riego_nota: str | None
    otros_cuidados: str | None
    created_at: datetime
    diagnosticos: list[DiagnosticoResumen]