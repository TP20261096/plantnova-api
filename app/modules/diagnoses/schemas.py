from datetime import datetime

from pydantic import BaseModel


class PrediccionOut(BaseModel):
    #Clase candidata devuelta por el modelo.

    clase_raw: str
    nombre_enfermedad: str | None
    confianza: float


class RecetaOut(BaseModel):
    #Remedio casero con sus pasos de preparación.

    nombre: str
    descripcion: str | None
    ingredientes: list[dict]
    preparacion: list[str]
    modo_uso: str | None
    precauciones: str | None
    costo_aprox: str | None
    frecuencia_dias: int
    num_aplicaciones: int
    nota: str | None


class DiagnosticoOut(BaseModel):

    id: str
    plant_id: str | None

    estado: str
    cultivo: str | None
    especie_slug: str | None
    nombre_enfermedad: str
    nombre_cientifico: str | None
    confianza: float
    confianza_baja: bool
    especie_confirmada: bool
    urgencia: str
    top3: list[PrediccionOut]

    descripcion: str | None
    sintomas: str | None
    causas: str | None
    prevencion: str | None

    riego_frecuencia_dias: int | None
    riego_nota: str | None
    otros_cuidados: str | None

    tratamientos: list[RecetaOut]
    insumos_no_caseros: list[dict]

    imagen_url: str | None
    gradcam_url: str | None
    created_at: datetime


class VincularRequest(BaseModel):
    #Planta a la que se asocia un diagnóstico huérfano.

    plant_id: str