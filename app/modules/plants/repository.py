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


def listar(
    cliente: Client, user_id: str, estado: str | None = None
) -> list[dict]:
    
    consulta = (
        cliente.table("plants")
        .select("*, species(nombre_comun)")
        .eq("user_id", user_id)
    )
    if estado:
        consulta = consulta.eq("estado", estado)
    return consulta.order("created_at", desc=True).execute().data


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
            "id, estado, confianza, imagen_url, created_at, disease_id, "
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


def actividades_de_seguimiento(
    cliente: Client, user_id: str
) -> list[dict]:
    """
    Cada tarjeta del jardín muestra la próxima revisión o aplicación
    pendiente y, si ya no queda ninguna, la revisión que se completó.
    Resolverlo planta por planta costaba tres consultas por tarjeta.
    """
    respuesta = (
        cliente.table("activities")
        .select(
            "plant_id, tipo, estado, fecha_programada, "
            "fecha_completada"
        )
        .eq("user_id", user_id)
        .in_("tipo", ["Tratamiento", "Revision"])
        .or_(
            "estado.eq.Pendiente,"
            "and(tipo.eq.Revision,estado.eq.Completada)"
        )
        .execute()
    )
    return respuesta.data


def tratamientos_de(cliente: Client, disease_id: str) -> list[dict]:
    """Recetas asociadas a una enfermedad, con sus pautas.

    Solo se consulta para el detalle de una planta, así que no
    encarece el listado del jardín.

    Args:
        cliente: Cliente Supabase del usuario.
        disease_id: UUID de la enfermedad del diagnóstico vigente.

    Returns:
        Filas de disease_treatments con la receta embebida.
    """
    respuesta = (
        cliente.table("disease_treatments")
        .select(
            "frecuencia_dias, num_aplicaciones, nota, "
            "recetas(nombre, descripcion, ingredientes, preparacion, "
            "modo_uso, precauciones, costo_aprox, fuentes)"
        )
        .eq("disease_id", disease_id)
        .order("prioridad", desc=False)
        .order("frecuencia_dias", desc=False)
        .execute()
    )
    return respuesta.data