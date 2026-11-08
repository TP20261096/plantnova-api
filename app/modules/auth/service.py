from fastapi import HTTPException, status
try:  
    from supabase_auth.errors import AuthApiError
except ImportError: 
    from gotrue.errors import AuthApiError

from app.core.security import CurrentUser
from app.core.supabase import anon_client, user_client
from app.modules.auth.schemas import (
    LoginRequest,
    RegistroRequest,
    SesionResponse,
    UsuarioResponse,
)

def usuario_actual(usuario: CurrentUser) -> UsuarioResponse:
    #Devuelve la identidad del usuario con su nombre de perfil.
    perfil = (
        user_client(usuario.token)
        .table("profiles")
        .select("nombre")
        .eq("id", usuario.id)
        .limit(1)
        .execute()
    )
    return UsuarioResponse(
        id=usuario.id,
        email=usuario.email,
        nombre=perfil.data[0]["nombre"] if perfil.data else None,
    )

def _a_sesion(respuesta) -> SesionResponse:
    
    if respuesta.session is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "La cuenta requiere confirmación por correo antes de "
                "iniciar sesión"
            ),
        )

    metadata = respuesta.user.user_metadata or {}
    return SesionResponse(
        access_token=respuesta.session.access_token,
        refresh_token=respuesta.session.refresh_token,
        expires_in=respuesta.session.expires_in,
        usuario=UsuarioResponse(
            id=respuesta.user.id,
            email=respuesta.user.email,
            nombre=metadata.get("nombre"),
        ),
    )


def registrar(datos: RegistroRequest) -> SesionResponse:
    
    try:
        respuesta = anon_client().auth.sign_up(
            {
                "email": datos.email,
                "password": datos.password,
                "options": {"data": {"nombre": datos.nombre}},
            }
        )
    except AuthApiError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.message,
        ) from exc

    return _a_sesion(respuesta)


def iniciar_sesion(datos: LoginRequest) -> SesionResponse:
    
    try:
        respuesta = anon_client().auth.sign_in_with_password(
            {"email": datos.email, "password": datos.password}
        )
    except AuthApiError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos",
        ) from exc

    return _a_sesion(respuesta)


def refrescar(refresh_token: str) -> SesionResponse:
    
    try:
        respuesta = anon_client().auth.refresh_session(refresh_token)
    except AuthApiError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sesión expirada, vuelve a iniciar sesión",
        ) from exc

    return _a_sesion(respuesta)


def cerrar_sesion(token: str) -> None:
    """Cierra solo la sesión de este dispositivo.

    El alcance es "local" a propósito. Con el alcance por defecto, "global",
    sign_out revoca todos los refresh tokens del usuario: cerrar sesión en
    el móvil echaría también al mismo usuario de cualquier otro dispositivo.

    Se usa admin.sign_out directamente en lugar de set_session + sign_out
    porque set_session con un refresh token vacío lanza excepción cuando el
    token de acceso ya venció, y además guarda la sesión en el cliente.
    """
    try:
        anon_client().auth.admin.sign_out(token, "local")
    except AuthApiError:
        # El token ya no vale: la sesión que se quería cerrar no existe,
        # que es justo el estado deseado.
        return