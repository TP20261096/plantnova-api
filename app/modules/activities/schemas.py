from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

TipoActividad = Literal["Riego", "Tratamiento", "Revision"]
EstadoActividad = Literal["Pendiente", "Completada", "Cancelada"]


class ActividadCreate(BaseModel):
    #Actividad creada manualmente por el usuario.

    plant_id: str
    tipo: TipoActividad
    titulo: str = Field(min_length=1, max_length=80)
    descripcion: str | None = None
    fecha_programada: date


class ActividadUpdate(BaseModel):

    titulo: str | None = Field(default=None, min_length=1, max_length=80)
    descripcion: str | None = None
    fecha_programada: date | None = None
    estado: EstadoActividad | None = None


class ActividadOut(BaseModel):
    
    id: str | None
    plant_id: str
    planta: str | None
    tipo: TipoActividad
    estado: EstadoActividad
    titulo: str
    descripcion: str | None
    fecha_programada: date
    fecha_completada: date | None
    dias_atraso: int
    aplicacion_num: int | None
    total_aplicaciones: int | None
    receta_nombre: str | None
    diagnosis_id: str | None
    proyectada: bool = False