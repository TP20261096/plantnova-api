from fastapi import APIRouter, Depends, Query

from app.core.security import CurrentUser, get_current_user
from app.modules.guide import service
from app.modules.guide.schemas import EspecieDetalle, EspecieResumen

router = APIRouter(prefix="/guide", tags=["Guía"])


@router.get(
    "/species",
    response_model=list[EspecieResumen],
    summary="Lista las especies de la guía",
)
def listar(
    q: str | None = Query(
        default=None,
        description="Busca por nombre común",
        max_length=60,
    ),
    diagnosticables: bool | None = Query(
        default=None,
        description="Filtra las especies que el modelo puede analizar",
    ),
    usuario: CurrentUser = Depends(get_current_user),
) -> list[EspecieResumen]:
    
    return service.listar_especies(usuario, q, diagnosticables)


@router.get(
    "/species/{slug}",
    response_model=EspecieDetalle,
    summary="Ficha completa de una especie",
)
def detalle(
    slug: str,
    usuario: CurrentUser = Depends(get_current_user),
) -> EspecieDetalle:
    #Devuelve preparación, siembra, cuidados, cosecha y consejos.
    return service.obtener_especie(usuario, slug)