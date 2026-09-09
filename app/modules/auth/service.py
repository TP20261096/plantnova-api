from fastapi import HTTPException, status
try:  
    from supabase_auth.errors import AuthApiError
except ImportError: 
    from gotrue.errors import AuthApiError

from app.core.supabase import anon_client
from app.modules.auth.schemas import (
    LoginRequest,
    RegistroRequest,
    SesionResponse,
    UsuarioResponse,
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
    
    cliente = anon_client()
    cliente.auth.set_session(token, "")
    cliente.auth.sign_out()