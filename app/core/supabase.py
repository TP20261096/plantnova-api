from functools import lru_cache

from supabase import Client, ClientOptions, create_client

from app.core.config import settings


def _opciones_sin_sesion() -> ClientOptions:
    """Opciones para un cliente que no debe guardar la sesión de nadie.

    Por defecto el cliente de Supabase almacena en memoria la sesión del
    último usuario que entró y arranca un temporizador que la renueva solo.
    En un servidor eso es doblemente dañino: la sesión queda como estado
    global compartido entre peticiones, y al renovarse por su cuenta
    Supabase rota el refresh token e invalida el que tiene la aplicación
    móvil, que a la siguiente petición recibe un 401 sin motivo.
    """
    return ClientOptions(
        auto_refresh_token=False,
        persist_session=False,
    )


def anon_client() -> Client:
    """Cliente con la clave pública, uno nuevo por uso.

    Sin caché a propósito: este cliente interviene en login, registro y
    renovación, y compartir su sesión entre usuarios mezcla identidades.
    Crearlo es barato comparado con el riesgo.
    """
    return create_client(
        settings.supabase_url,
        settings.supabase_publishable_key,
        options=_opciones_sin_sesion(),
    )


def user_client(token: str) -> Client:
    
    cliente = create_client(
        settings.supabase_url,
        settings.supabase_publishable_key,
        options=_opciones_sin_sesion(),
    )
    cliente.postgrest.auth(token)
    return cliente


@lru_cache
def service_client() -> Client:
    """Cliente con la clave de servicio. Se cachea porque nunca sostiene la
    sesión de un usuario: actúa siempre con su propia identidad."""
    return create_client(
        settings.supabase_url,
        settings.supabase_secret_key,
        options=_opciones_sin_sesion(),
    )
