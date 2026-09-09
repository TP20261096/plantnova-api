from fastapi import APIRouter, Depends, status

from app.core.security import CurrentUser, get_current_user
from app.modules.profile import service
from app.modules.profile.schemas import (
    DISTRITOS_LIMA,
    PasswordUpdate,
    PerfilOut,
    PerfilUpdate,
)

router = APIRouter(prefix="/profile", tags=["Perfil"])


@router.get(
    "",
    response_model=PerfilOut,
    summary="Devuelve el perfil del usuario",
)
def obtener(
    usuario: CurrentUser = Depends(get_current_user),
) -> PerfilOut:
    #Datos personales, preferencias y total de plantas.
    return service.obtener_perfil(usuario)


@router.patch(
    "",
    response_model=PerfilOut,
    summary="Actualiza el perfil",
)
def actualizar(
    cambios: PerfilUpdate,
    usuario: CurrentUser = Depends(get_current_user),
) -> PerfilOut:
    """Modifica nombre, foto, distrito o notificaciones."""
    return service.actualizar_perfil(usuario, cambios)


@router.get(
    "/districts",
    response_model=list[str],
    summary="Lista los distritos admitidos",
)
def distritos() -> list[str]:
    """Alimenta el selector de distrito de la app."""
    return DISTRITOS_LIMA


@router.put(
    "/password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cambia la contraseña",
)
def cambiar_password(
    datos: PasswordUpdate,
    usuario: CurrentUser = Depends(get_current_user),
) -> None:
    #Requiere la contraseña actual para autorizar el cambio.
    service.cambiar_password(usuario, datos)


@router.delete(
    "",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Elimina la cuenta y todos sus datos",
)
def eliminar(
    usuario: CurrentUser = Depends(get_current_user),
) -> None:
    #Borra la cuenta de forma irreversible.
    service.eliminar_cuenta(usuario)