"""Endpoints del módulo Jardín."""

from fastapi import APIRouter, Depends, status

from app.core.security import CurrentUser, get_current_user
from app.modules.plants import service
from app.modules.plants.schemas import (
    PlantaCreate,
    PlantaDetalle,
    PlantaResumen,
    PlantaUpdate,
)

router = APIRouter(prefix="/plants", tags=["Jardín"])


@router.post(
    "",
    response_model=PlantaResumen,
    status_code=status.HTTP_201_CREATED,
    summary="Registra una nueva planta",
)
def crear(
    datos: PlantaCreate,
    usuario: CurrentUser = Depends(get_current_user),
) -> PlantaResumen:
    """Agrega una planta al jardín del usuario."""
    return service.crear_planta(usuario, datos)


@router.get(
    "",
    response_model=list[PlantaResumen],
    summary="Lista las plantas del usuario",
)
def listar(
    usuario: CurrentUser = Depends(get_current_user),
) -> list[PlantaResumen]:
    """Devuelve todas las plantas registradas."""
    return service.listar_plantas(usuario)


@router.get(
    "/{planta_id}",
    response_model=PlantaDetalle,
    summary="Detalle de una planta con su historial",
)
def detalle(
    planta_id: str,
    usuario: CurrentUser = Depends(get_current_user),
) -> PlantaDetalle:
    """Devuelve los datos de la planta y sus diagnósticos previos."""
    return service.obtener_planta(usuario, planta_id)


@router.put(
    "/{planta_id}",
    response_model=PlantaResumen,
    summary="Actualiza los datos de una planta",
)
def actualizar(
    planta_id: str,
    cambios: PlantaUpdate,
    usuario: CurrentUser = Depends(get_current_user),
) -> PlantaResumen:
    """Modifica apodo, ubicación, etapa, especie o fecha de siembra."""
    return service.actualizar_planta(usuario, planta_id, cambios)


@router.delete(
    "/{planta_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Elimina una planta del jardín",
)
def eliminar(
    planta_id: str,
    usuario: CurrentUser = Depends(get_current_user),
) -> None:
    """Borra la planta junto con su historial y sus actividades."""
    service.eliminar_planta(usuario, planta_id)