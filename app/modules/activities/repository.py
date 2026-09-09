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
        .select(
            "receta_id, frecuencia_dias, num_aplicaciones, nota, "
            "recetas(nombre)"
        )
        .eq("disease_id", disease_id)
        .limit(1)
        .execute()
    )
    return respuesta.data[0] if respuesta.data else None