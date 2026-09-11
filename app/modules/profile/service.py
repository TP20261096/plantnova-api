from fastapi import HTTPException, status

from app.core.security import CurrentUser
from app.core.supabase import anon_client, service_client, user_client
from app.modules.auth.service import AuthApiError
from app.modules.profile.schemas import (
    DISTRITOS_LIMA,
    PasswordUpdate,
    PerfilOut,
    PerfilUpdate,
)


def _cargar(usuario: CurrentUser) -> PerfilOut:
    
    cliente = user_client(usuario.token)

    perfil = (
        cliente.table("profiles")
        .select("*")
        .eq("id", usuario.id)
        .limit(1)
        .execute()
    )
    if not perfil.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El perfil no existe",
        )

    plantas = (
        cliente.table("plants")
        .select("id", count="exact")
        .eq("user_id", usuario.id)
        .execute()
    )

    fila = perfil.data[0]
    return PerfilOut(
        id=fila["id"],
        email=usuario.email,
        nombre=fila.get("nombre"),
        foto_url=fila.get("foto_url"),
        distrito=fila.get("distrito"),
        notificaciones=fila["notificaciones"],
        plantas_registradas=plantas.count or 0,
        created_at=fila["created_at"],
    )


def obtener_perfil(usuario: CurrentUser) -> PerfilOut:
    
    return _cargar(usuario)


def actualizar_perfil(
    usuario: CurrentUser, cambios: PerfilUpdate
) -> PerfilOut:
    
    valores = cambios.model_dump(exclude_unset=True)
    if not valores:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se envió ningún campo para actualizar",
        )

    distrito = valores.get("distrito")
    if distrito and distrito not in DISTRITOS_LIMA:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El distrito no está en la lista admitida",
        )

    cliente = user_client(usuario.token)
    cliente.table("profiles").update(valores).eq(
        "id", usuario.id
    ).execute()

    return _cargar(usuario)


def cambiar_password(
    usuario: CurrentUser, datos: PasswordUpdate
) -> None:
    
    if not usuario.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La cuenta no tiene un correo asociado",
        )

    cliente = anon_client()
    try:
        cliente.auth.sign_in_with_password(
            {
                "email": usuario.email,
                "password": datos.password_actual,
            }
        )
    except AuthApiError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="La contraseña actual no es correcta",
        ) from exc

    try:
        cliente.auth.update_user({"password": datos.password_nueva})
    except AuthApiError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.message,
        ) from exc


def eliminar_cuenta(usuario: CurrentUser) -> None:
    
    cliente = service_client()

    try:
        bucket = cliente.storage.from_("diagnoses")
        rutas = []
        # list no es recursivo: hay que recorrer cada subcarpeta.
        for carpeta in (usuario.id, f"{usuario.id}/plants"):
            for archivo in bucket.list(carpeta):
                rutas.append(f"{carpeta}/{archivo['name']}")
        if rutas:
            bucket.remove(rutas)
    except Exception:  # noqa: BLE001
        # Un fallo al limpiar imágenes no debe impedir que el usuario
        # elimine su cuenta.
        pass

    try:
        cliente.auth.admin.delete_user(usuario.id)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo eliminar la cuenta",
        ) from exc