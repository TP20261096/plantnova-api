from datetime import datetime
from app.core.distritos import DISTRITOS
from pydantic import BaseModel, Field
from typing import Literal

Tema = Literal["Sistema", "Claro", "Oscuro"]


DISTRITOS_LIMA = sorted(DISTRITOS)


class PerfilOut(BaseModel):

    id: str
    email: str | None
    nombre: str | None
    foto_url: str | None
    distrito: str | None
    notificaciones: bool
    tema: Tema
    plantas_registradas: int
    diagnosticos_realizados: int
    tareas_pendientes: int
    tareas_completadas: int
    created_at: datetime


class PerfilUpdate(BaseModel):
    #Campos editables del perfil.

    nombre: str | None = Field(default=None, min_length=2, max_length=60)
    foto_url: str | None = None
    distrito: str | None = None
    notificaciones: bool | None = None
    tema: Tema | None = None


class PasswordUpdate(BaseModel):

    # La actual solo se verifica, no se establece: exigirle 8 caracteres
    # devolvia un 422 de validacion en lugar de "La contraseña actual es
    # incorrecta" cuando el usuario escribia una contrasena corta y erronea.
    password_actual: str = Field(min_length=1, max_length=72)
    password_nueva: str = Field(min_length=8, max_length=72)