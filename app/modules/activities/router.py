from datetime import date

from fastapi import APIRouter, Depends, Query, status

from app.core.security import CurrentUser, get_current_user
from app.modules.activities import service
from app.modules.activities.schemas import (
    ActividadCreate,
    ActividadOut,
    ActividadUpdate,
)

router = APIRouter(prefix="/activities", tags=["Actividades"])


@router.get(
    "",
    response_model=list[ActividadOut],
    summary="Agenda de actividades de un día",
)
def agenda(
    fecha: date | None = Query(
        default=None,
        description="Día consultado. Por defecto, hoy",
    ),
    usuario: CurrentUser = Depends(get_current_user),
) -> list[ActividadOut]:
    
    return service.listar_agenda(usuario, fecha)


@router.post(
    "",
    response_model=ActividadOut,
    status_code=status.HTTP_201_CREATED,
    summary="Crea una actividad manual",
)
def crear(
    datos: ActividadCreate,
    usuario: CurrentUser = Depends(get_current_user),
) -> ActividadOut:
    #Agrega una tarea que el usuario define por su cuenta.
    return service.crear_actividad(usuario, datos)


@router.patch(
    "/{actividad_id}",
    response_model=ActividadOut,
    summary="Edita o completa una actividad",
)
def actualizar(
    actividad_id: str,
    cambios: ActividadUpdate,
    usuario: CurrentUser = Depends(get_current_user),
) -> ActividadOut:
    #Marcar Completada encadena la siguiente ocurrencia.
    return service.actualizar_actividad(usuario, actividad_id, cambios)


@router.delete(
    "/{actividad_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Elimina una actividad",
)
def eliminar(
    actividad_id: str,
    usuario: CurrentUser = Depends(get_current_user),
) -> None:
    #Borra la tarea indicada.
    service.eliminar_actividad(usuario, actividad_id)