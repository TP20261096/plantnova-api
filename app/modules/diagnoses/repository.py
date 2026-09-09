from supabase import Client

# La ficha completa de la enfermedad, con sus recetas asociadas, se
# obtiene en una sola consulta anidada. Evita tres viajes a la base
# justo después de la inferencia, que es la parte lenta del proceso.
_FICHA = (
    "*, species(slug, nombre_comun), "
    "disease_treatments(frecuencia_dias, num_aplicaciones, nota, "
    "recetas(nombre, descripcion, ingredientes, preparacion, "
    "modo_uso, precauciones, costo_aprox))"
)


def buscar_ficha(cliente: Client, clase_raw: str) -> dict | None:
    
    respuesta = (
        cliente.table("disease_catalog")
        .select(_FICHA)
        .eq("clase_raw", clase_raw)
        .limit(1)
        .execute()
    )
    return respuesta.data[0] if respuesta.data else None


def nombres_por_clase(
    cliente: Client, clases: list[str]
) -> dict[str, str]:
    
    respuesta = (
        cliente.table("disease_catalog")
        .select("clase_raw, nombre_enfermedad")
        .in_("clase_raw", clases)
        .execute()
    )
    return {
        f["clase_raw"]: f["nombre_enfermedad"] for f in respuesta.data
    }


def crear(cliente: Client, datos: dict) -> dict:
    
    return cliente.table("diagnoses").insert(datos).execute().data[0]


def obtener(cliente: Client, diagnostico_id: str) -> dict | None:
    
    respuesta = (
        cliente.table("diagnoses")
        .select("*")
        .eq("id", diagnostico_id)
        .limit(1)
        .execute()
    )
    return respuesta.data[0] if respuesta.data else None


def actualizar(
    cliente: Client, diagnostico_id: str, cambios: dict
) -> dict:
    
    respuesta = (
        cliente.table("diagnoses")
        .update(cambios)
        .eq("id", diagnostico_id)
        .execute()
    )
    return respuesta.data[0]