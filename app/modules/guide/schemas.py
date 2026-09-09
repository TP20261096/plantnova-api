"""Contratos de salida del módulo Guía."""

from typing import Literal

from pydantic import BaseModel

Seccion = Literal[
    "Preparacion", "Siembra", "Cuidados", "Cosecha", "Consejos"
]


class EspecieResumen(BaseModel):
    #Tarjeta de especie para el listado de la guía.

    id: str
    slug: str
    nombre_comun: str
    nombre_cientifico: str | None
    imagen_url: str | None
    resumen: str
    dificultad: str
    riego_base_dias: int
    diagnosticable: bool


class SeccionGuia(BaseModel):
    #Bloque de contenido de una especie.

    seccion: Seccion
    contenido: str


class EspecieDetalle(EspecieResumen):
    
    familia: str | None
    luz_recomendada: str | None
    secciones: list[SeccionGuia]