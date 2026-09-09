from fastapi import HTTPException, status

from app.core.security import CurrentUser
from app.core.supabase import user_client
from app.modules.guide import repository as repo
from app.modules.guide.schemas import (
    EspecieDetalle,
    EspecieResumen,
    SeccionGuia,
)

_ORDEN_SECCIONES = [
    "Preparacion",
    "Siembra",
    "Cuidados",
    "Cosecha",
    "Consejos",
]


def listar_especies(
    usuario: CurrentUser,
    busqueda: str | None = None,
    solo_diagnosticables: bool | None = None,
) -> list[EspecieResumen]:
    
    cliente = user_client(usuario.token)
    filas = repo.listar(cliente, busqueda, solo_diagnosticables)
    return [EspecieResumen(**fila) for fila in filas]


def obtener_especie(usuario: CurrentUser, slug: str) -> EspecieDetalle:
    
    cliente = user_client(usuario.token)
    fila = repo.obtener_por_slug(cliente, slug)
    if fila is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La especie no existe en la guía",
        )

    secciones = fila.pop("species_sections", []) or []
    secciones.sort(key=lambda s: _ORDEN_SECCIONES.index(s["seccion"]))

    return EspecieDetalle(
        **fila,
        secciones=[SeccionGuia(**s) for s in secciones],
    )