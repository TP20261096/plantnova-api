"""Endpoint de clima para la pantalla de Inicio."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.clima import clima_actual
from app.core.security import CurrentUser, get_current_user
from app.core.supabase import user_client
from app.modules.weather.schemas import ClimaOut

router = APIRouter(prefix="/weather", tags=["Clima"])


@router.get(
    "",
    response_model=ClimaOut,
    summary="Clima actual del distrito del usuario",
)
def actual(
    usuario: CurrentUser = Depends(get_current_user),
) -> ClimaOut:
    """Devuelve temperatura, humedad y viento del momento.

    Usa el distrito registrado en el perfil. Si el usuario no eligió
    ninguno se informa el de Lima centro, sin pedirle permisos de
    ubicación en ningún caso.
    """
    perfil = (
        user_client(usuario.token)
        .table("profiles")
        .select("distrito")
        .eq("id", usuario.id)
        .limit(1)
        .execute()
    )
    distrito = perfil.data[0]["distrito"] if perfil.data else None

    clima = clima_actual(distrito)
    if clima is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="El servicio de clima no está disponible",
        )
    return ClimaOut(
        ciudad=distrito or "Lima Metropolitana",
        temperatura=clima.temperatura,
        humedad=clima.humedad,
        viento_kmh=clima.viento_kmh,
        observado=clima.observado,
    )