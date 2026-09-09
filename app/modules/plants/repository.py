"""Acceso a datos del módulo Jardín.

Todas las consultas se ejecutan con el cliente del usuario, de modo
que las políticas RLS filtran por user_id en la propia base de datos.
El filtro explícito que aparece en algunas consultas es una segunda
barrera, no la principal.
"""

from supabase import Client


def crear(cliente: Client, datos: dict) -> dict:
    """Inserta una planta.

    Args:
        cliente: Cliente Supabase del usuario.
        datos: Fila lista para insertar.

    Returns:
        La planta creada.
    """
    respuesta = cliente.table("plants").insert(datos).execute()
    return respuesta.data[0]


def listar(cliente: Client, user_id: str) -> list[dict]:
    """Devuelve las plantas del usuario con el nombre de su especie.

    Args:
        cliente: Cliente Supabase del usuario.
        user_id: UUID del usuario.

    Returns:
        Filas de plants con la especie embebida.
    """
    respuesta = (
        cliente.table("plants")
        .select("*, species(nombre_comun)")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    )
    return respuesta.data


def obtener(cliente: Client, planta_id: str) -> dict | None:
    """Busca una planta por su identificador.

    Args:
        cliente: Cliente Supabase del usuario.
        planta_id: UUID de la planta.

    Returns:
        La planta, o None si no existe o pertenece a otro usuario.
    """
    respuesta = (
        cliente.table("plants")
        .select("*, species(nombre_comun, riego_base_dias)")
        .eq("id", planta_id)
        .limit(1)
        .execute()
    )
    return respuesta.data[0] if respuesta.data else None


def actualizar(cliente: Client, planta_id: str, cambios: dict) -> dict:
    """Aplica cambios parciales a una planta.

    Args:
        cliente: Cliente Supabase del usuario.
        planta_id: UUID de la planta.
        cambios: Columnas a modificar.

    Returns:
        La planta ya actualizada.
    """
    respuesta = (
        cliente.table("plants")
        .update(cambios)
        .eq("id", planta_id)
        .execute()
    )
    return respuesta.data[0]


def eliminar(cliente: Client, planta_id: str) -> None:
    """Elimina una planta y, en cascada, su historial y actividades.

    Args:
        cliente: Cliente Supabase del usuario.
        planta_id: UUID de la planta.
    """
    cliente.table("plants").delete().eq("id", planta_id).execute()


def historial(cliente: Client, planta_id: str) -> list[dict]:
    """Devuelve los diagnósticos de una planta, del más reciente al
    más antiguo.

    Args:
        cliente: Cliente Supabase del usuario.
        planta_id: UUID de la planta.

    Returns:
        Filas de diagnoses con el nombre de la enfermedad.
    """
    respuesta = (
        cliente.table("diagnoses")
        .select(
            "id, estado, confianza, imagen_url, created_at, "
            "disease_catalog(nombre_enfermedad, riego_frecuencia_dias, "
            "riego_nota, otros_cuidados)"
        )
        .eq("plant_id", planta_id)
        .order("created_at", desc=True)
        .execute()
    )
    return respuesta.data


def tiene_tratamiento_pendiente(cliente: Client, planta_id: str) -> bool:
    """Indica si quedan aplicaciones de tratamiento sin completar.

    Args:
        cliente: Cliente Supabase del usuario.
        planta_id: UUID de la planta.

    Returns:
        True si existe al menos una actividad de tratamiento
        pendiente.
    """
    respuesta = (
        cliente.table("activities")
        .select("id")
        .eq("plant_id", planta_id)
        .eq("tipo", "Tratamiento")
        .eq("estado", "Pendiente")
        .limit(1)
        .execute()
    )
    return bool(respuesta.data)