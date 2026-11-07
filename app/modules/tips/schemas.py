"""Contrato de salida de los consejos generales."""

from pydantic import BaseModel


class ConsejoOut(BaseModel):
    """Consejo de la sección "Consejos para tus plantas"."""

    id: str
    slug: str
    titulo: str
    contenido: str
