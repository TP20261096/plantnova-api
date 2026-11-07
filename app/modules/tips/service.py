"""Lógica de los consejos generales."""

from app.core.security import CurrentUser
from app.core.supabase import user_client
from app.modules.tips import repository as repo
from app.modules.tips.schemas import ConsejoOut


def listar_consejos(usuario: CurrentUser) -> list[ConsejoOut]:
    """Devuelve los consejos que muestra la pantalla de Inicio.

    No dependen de las plantas del usuario: HU036 pide que se vean
    aunque el jardín esté vacío.

    Args:
        usuario: Usuario autenticado.

    Returns:
        Lista de consejos en orden de presentación.
    """
    cliente = user_client(usuario.token)
    return [ConsejoOut(**fila) for fila in repo.listar(cliente)]
