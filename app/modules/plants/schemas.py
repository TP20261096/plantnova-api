"""Contratos de entrada y salida del módulo Jardín."""

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
    """Datos para registrar una planta.

    species_id es opcional a propósito: si el usuario cultiva una
    especie que no está en el catálogo debe poder registrarla igual.
    En ese caso el riego parte de un valor por defecto hasta que
    exista un diagnóstico.
    """

    apodo: str = Field(min_length=1, max_length=60)
    ubicacion: Ubicacion
    etapa: Etapa = "Crecimiento"
    species_id: str | None = None
    fecha_siembra: date | None = None
    foto_url: str | None = None


class PlantaUpdate(BaseModel):
    """Campos editables de una planta.

    No incluye estado ni riego_frecuencia_dias: ambos los deriva el
    backend y el cliente no debe poder sobrescribirlos.
    """

    apodo: str | None = Field(default=None, min_length=1, max_length=60)
    ubicacion: Ubicacion | None = None
    etapa: Etapa | None = None
    species_id: str | None = None
    fecha_siembra: date | None = None
    foto_url: str | None = None


class PlantaResumen(BaseModel):
    """Tarjeta de planta para el listado del jardín."""

    id: str
    apodo: str
    especie: str | None
    ubicacion: Ubicacion
    etapa: Etapa
    estado: EstadoPlanta
    foto_url: str | None
    riego_frecuencia_dias: int | None
    ultimo_riego: date | None
    proximo_riego: date | None
    dias_para_riego: int | None


class DiagnosticoResumen(BaseModel):
    """Entrada del historial de diagnósticos de una planta."""

    id: str
    nombre_enfermedad: str | None
    estado: str
    confianza: float
    imagen_url: str
    created_at: datetime


class PlantaDetalle(PlantaResumen):
    """Vista completa de una planta con su historial."""

    species_id: str | None
    fecha_siembra: date | None
    riego_nota: str | None
    otros_cuidados: str | None
    created_at: datetime
    diagnosticos: list[DiagnosticoResumen]