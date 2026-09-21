"""Acceso a datos del módulo Jardín.

Todas las consultas se ejecutan con el cliente del usuario, de modo
que las políticas RLS filtran por user_id en la propia base de datos.
El filtro explícito que aparece en algunas consultas es una segunda
barrera, no la principal.
"""

from supabase import Client


def crear(cliente: Client, datos: dict) -> dict:
    """Inserta una planta."""
    respuesta = cliente.table("plants").insert(datos).execute()
    return respuesta.data[0]


def listar(cliente: Client, user_id: str) -> list[dict]:
    """Devuelve las plantas del usuario con el nombre de su especie."""
    respuesta = (
        cliente.table("plants")
        .select("*, species(nombre_comun)")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    )
    return respuesta.data


def obtener(cliente: Client, planta_id: str) -> dict | None:
    """Busca una planta por su identificador."""
    respuesta = (
        cliente.table("plants")
        .select("*, species(nombre_comun, riego_base_dias)")
        .eq("id", planta_id)
        .limit(1)
        .execute()
    )
    return respuesta.data[0] if respuesta.data else None


def actualizar(cliente: Client, planta_id: str, cambios: dict) -> dict:
    """Aplica cambios parciales a una planta."""
    respuesta = (
        cliente.table("plants")
        .update(cambios)
        .eq("id", planta_id)
        .execute()
    )
    return respuesta.data[0]


def eliminar(cliente: Client, planta_id: str) -> None:
    """Elimina una planta y, en cascada, su historial y actividades."""
    cliente.table("plants").delete().eq("id", planta_id).execute()


def historial(cliente: Client, planta_id: str) -> list[dict]:
    """Devuelve los diagnósticos de una planta, del más reciente al más antiguo."""
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
    """Indica si quedan aplicaciones de tratamiento sin completar."""
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


def proxima_actividad_tratamiento(cliente: Client, planta_id: str) -> dict | None:
    """Obtiene la actividad pendiente más próxima, priorizando revisiones si existen."""
    # 1. Buscar primero si hay una Revisión Pendiente
    revision = (
        cliente.table("activities")
        .select("*")
        .eq("plant_id", planta_id)
        .eq("tipo", "Revision")
        .eq("estado", "Pendiente")
        .order("fecha_programada", desc=False)
        .limit(1)
        .execute()
    )
    if revision.data:
        return revision.data[0]

    # 2. Si no hay revisión, buscar el Tratamiento pendiente
    respuesta = (
        cliente.table("activities")
        .select("*")
        .eq("plant_id", planta_id)
        .eq("tipo", "Tratamiento")
        .eq("estado", "Pendiente")
        .order("fecha_programada", desc=False)
        .limit(1)
        .execute()
    )
    return respuesta.data[0] if respuesta.data else None