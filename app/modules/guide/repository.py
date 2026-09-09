from supabase import Client

_CAMPOS_RESUMEN = (
    "id, slug, nombre_comun, nombre_cientifico, imagen_url, resumen, "
    "dificultad, riego_base_dias, diagnosticable"
)


def listar(
    cliente: Client,
    busqueda: str | None = None,
    solo_diagnosticables: bool | None = None,
) -> list[dict]:
    
    consulta = cliente.table("species").select(_CAMPOS_RESUMEN)

    if busqueda:
        consulta = consulta.ilike("nombre_comun", f"%{busqueda}%")
    if solo_diagnosticables is not None:
        consulta = consulta.eq("diagnosticable", solo_diagnosticables)

    return consulta.order("nombre_comun").execute().data


def obtener_por_slug(cliente: Client, slug: str) -> dict | None:
    
    respuesta = (
        cliente.table("species")
        .select(
            f"{_CAMPOS_RESUMEN}, familia, luz_recomendada, "
            "species_sections(seccion, contenido)"
        )
        .eq("slug", slug)
        .limit(1)
        .execute()
    )
    return respuesta.data[0] if respuesta.data else None