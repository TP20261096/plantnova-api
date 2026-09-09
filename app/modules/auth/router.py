"""Endpoints de autenticación."""

from fastapi import APIRouter, Depends, status

from app.core.security import CurrentUser, get_current_user
from app.modules.auth import service
from app.modules.auth.schemas import (
    LoginRequest,
    RefreshRequest,
    RegistroRequest,
    SesionResponse,
    UsuarioResponse,
)

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post(
    "/register",
    response_model=SesionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registra un nuevo usuario",
)
def register(datos: RegistroRequest) -> SesionResponse:
    #Crea la cuenta y devuelve la sesión iniciada.
    return service.registrar(datos)


@router.post(
    "/login",
    response_model=SesionResponse,
    summary="Autentica al usuario y retorna los tokens",
)
def login(datos: LoginRequest) -> SesionResponse:
    #Valida las credenciales y abre una sesión.
    return service.iniciar_sesion(datos)


@router.post(
    "/refresh",
    response_model=SesionResponse,
    summary="Renueva el token de acceso",
)
def refresh(datos: RefreshRequest) -> SesionResponse:
    #Entrega un token de acceso nuevo sin pedir la contraseña.
    return service.refrescar(datos.refresh_token)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cierra la sesión activa",
)
def logout(usuario: CurrentUser = Depends(get_current_user)) -> None:
    #Invalida la sesión del usuario en curso.
    service.cerrar_sesion(usuario.token)


@router.get(
    "/me",
    response_model=UsuarioResponse,
    summary="Devuelve el usuario del token",
)
def me(usuario: CurrentUser = Depends(get_current_user)) -> UsuarioResponse:
    #Permite a la app verificar si la sesión sigue siendo válida.
    return UsuarioResponse(
        id=usuario.id,
        email=usuario.email,
        nombre=None,
    )