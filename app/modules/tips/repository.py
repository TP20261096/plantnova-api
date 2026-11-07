"""Acceso a datos de los consejos generales.

Los consejos son catálogo: iguales para todos los usuarios y de solo
lectura, igual que las especies o las recetas.
"""

from supabase import Client


def listar(cliente: Client) -> list[dict]:
    """Devuelve los consejos en su orden de presentación.

    Args:
        cliente: Cliente Supabase del usuario.

    Returns:
        Filas de tips ordenadas por el campo orden.
    """
    respuesta = (
        cliente.table("tips")
        .select("id, slug, titulo, contenido")
        .order("orden", desc=False)
        .execute()
    )
    return respuesta.data
