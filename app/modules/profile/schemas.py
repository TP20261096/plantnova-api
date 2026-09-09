from datetime import datetime

from pydantic import BaseModel, Field

# Distritos con puntos de venta de insumos registrados en el
# catálogo. Se valida contra esta lista para que el filtro de
# insumos del diagnóstico no falle por un nombre mal escrito.
DISTRITOS_LIMA = [
    "Ate", "Barranco", "Breña", "Callao", "Carabayllo",
    "Chorrillos", "Comas", "El Agustino", "Independencia",
    "Jesús María", "La Molina", "La Victoria", "Lima",
    "Lince", "Los Olivos", "Lurín", "Magdalena del Mar",
    "Miraflores", "Pachacámac", "Pueblo Libre", "Puente Piedra",
    "Rímac", "San Borja", "San Isidro", "San Juan de Lurigancho",
    "San Juan de Miraflores", "San Luis", "San Martín de Porres",
    "San Miguel", "Santa Anita", "Santiago de Surco",
    "Surquillo", "Villa El Salvador", "Villa María del Triunfo",
]


class PerfilOut(BaseModel):

    id: str
    email: str | None
    nombre: str | None
    foto_url: str | None
    distrito: str | None
    notificaciones: bool
    plantas_registradas: int
    created_at: datetime


class PerfilUpdate(BaseModel):
    #Campos editables del perfil.

    nombre: str | None = Field(default=None, min_length=2, max_length=60)
    foto_url: str | None = None
    distrito: str | None = None
    notificaciones: bool | None = None


class PasswordUpdate(BaseModel):

    password_actual: str = Field(min_length=8, max_length=72)
    password_nueva: str = Field(min_length=8, max_length=72)