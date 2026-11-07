"""Endpoint de consejos generales."""

from fastapi import APIRouter, Depends

from app.core.security import CurrentUser, get_current_user
from app.modules.tips import service
from app.modules.tips.schemas import ConsejoOut

router = APIRouter(prefix="/tips", tags=["Consejos"])


@router.get(
    "",
    response_model=list[ConsejoOut],
    summary="Consejos generales para el cuidado de plantas",
)
def listar(
    usuario: CurrentUser = Depends(get_current_user),
) -> list[ConsejoOut]:
    """Alimenta el carrusel "Consejos para tus plantas" de Inicio."""
    return service.listar_consejos(usuario)
