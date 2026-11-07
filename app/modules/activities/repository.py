from datetime import date

from supabase import Client

_CAMPOS = "*, plants(apodo), recetas(nombre)"


def agenda(cliente: Client, user_id: str, dia: date) -> list[dict]:
    
    iso = dia.isoformat()

    pendientes = (
        cliente.table("activities")
        .select(_CAMPOS)
        .eq("user_id", user_id)
        .eq("estado", "Pendiente")
        .lte("fecha_programada", iso)
        .execute()
    )
    cerradas = (
        cliente.table("activities")
        .select(_CAMPOS)
        .eq("user_id", user_id)
        .neq("estado", "Pendiente")
        .eq("fecha_completada", iso)
        .execute()
    )
    return pendientes.data + cerradas.data


def programadas_desde(
    cliente: Client, user_id: str, dia: date
) -> list[dict]:
    
    respuesta = (
        cliente.table("activities")
        .select(_CAMPOS)
        .eq("user_id", user_id)
        .eq("estado", "Pendiente")
        .eq("fecha_programada", dia.isoformat())
        .execute()
    )
    return respuesta.data


def obtener(cliente: Client, actividad_id: str) -> dict | None:
    
    respuesta = (
        cliente.table("activities")
        .select(_CAMPOS)
        .eq("id", actividad_id)
        .limit(1)
        .execute()
    )
    return respuesta.data[0] if respuesta.data else None


def pendiente_de_tipo(
    cliente: Client, plant_id: str, tipo: str
) -> dict | None:
    
    respuesta = (
        cliente.table("activities")
        .select("*")
        .eq("plant_id", plant_id)
        .eq("tipo", tipo)
        .eq("estado", "Pendiente")
        .limit(1)
        .execute()
    )
    return respuesta.data[0] if respuesta.data else None


def crear(cliente: Client, datos: dict) -> dict:
    
    return cliente.table("activities").insert(datos).execute().data[0]


def actualizar(
    cliente: Client, actividad_id: str, cambios: dict
) -> dict:
    
    respuesta = (
        cliente.table("activities")
        .update(cambios)
        .eq("id", actividad_id)
        .execute()
    )
    return respuesta.data[0]


def eliminar(cliente: Client, actividad_id: str) -> None:
    
    cliente.table("activities").delete().eq(
        "id", actividad_id
    ).execute()


def cancelar_pendientes(
    cliente: Client, plant_id: str, tipos: list[str]
) -> None:
    
    (
        cliente.table("activities")
        .update({"estado": "Cancelada"})
        .eq("plant_id", plant_id)
        .eq("estado", "Pendiente")
        .in_("tipo", tipos)
        .execute()
    )


def tratamiento_de_enfermedad(
    cliente: Client, disease_id: str
) -> dict | None:
    
    respuesta = (
        cliente.table("disease_treatments")
        .select("*, recetas(*)")
        .eq("disease_id", disease_id)
        .order("prioridad", desc=False)
        .order("frecuencia_dias", desc=False)
        .limit(1)
        .execute()
    )
    return respuesta.data[0] if respuesta.data else None


def plantas_con_pendiente(
    cliente: Client, user_id: str, tipo: str
) -> set[str]:
    """Ids de las plantas que ya tienen una tarea pendiente del tipo.

    Evita preguntarlo planta por planta al materializar o proyectar
    los riegos.

    Args:
        cliente: Cliente Supabase del usuario.
        user_id: UUID del usuario.
        tipo: Valor del enum tipo_actividad.

    Returns:
        Conjunto de plant_id con una tarea pendiente de ese tipo.
    """
    respuesta = (
        cliente.table("activities")
        .select("plant_id")
        .eq("user_id", user_id)
        .eq("tipo", tipo)
        .eq("estado", "Pendiente")
        .execute()
    )
    return {fila["plant_id"] for fila in respuesta.data}


def rango(
    cliente: Client, user_id: str, desde: date, hasta: date
) -> tuple[list[dict], list[dict]]:
    """Trae las tareas que pueden aparecer en una ventana de días.

    Las pendientes se piden sin límite inferior a propósito: una
    tarea atrasada sigue exigiendo atención y debe aparecer en los
    días posteriores a su fecha.

    Args:
        cliente: Cliente Supabase del usuario.
        user_id: UUID del usuario.
        desde: Primer día de la ventana.
        hasta: Último día de la ventana.

    Returns:
        Las tareas pendientes y las cerradas dentro de la ventana.
    """
    pendientes = (
        cliente.table("activities")
        .select(_CAMPOS)
        .eq("user_id", user_id)
        .eq("estado", "Pendiente")
        .lte("fecha_programada", hasta.isoformat())
        .execute()
    )
    cerradas = (
        cliente.table("activities")
        .select(_CAMPOS)
        .eq("user_id", user_id)
        .neq("estado", "Pendiente")
        .gte("fecha_completada", desde.isoformat())
        .lte("fecha_completada", hasta.isoformat())
        .execute()
    )
    return pendientes.data, cerradas.data

def proxima_pendiente(cliente: Client, user_id: str) -> dict | None:
    """Devuelve la tarea pendiente más próxima del usuario.

    Mira todo el jardín, no solo la planta de la tarea que se acaba
    de completar: lo que el usuario necesita saber es qué toca
    ahora, sea de la planta que sea.

    Args:
        cliente: Cliente Supabase del usuario.
        user_id: UUID del usuario.

    Returns:
        La actividad pendiente más cercana, o None si no queda
        ninguna.
    """
    respuesta = (
        cliente.table("activities")
        .select(_CAMPOS)
        .eq("user_id", user_id)
        .eq("estado", "Pendiente")
        .order("fecha_programada", desc=False)
        .limit(1)
        .execute()
    )
    return respuesta.data[0] if respuesta.data else None