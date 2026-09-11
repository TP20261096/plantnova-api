from app.core.config import settings
from app.core.supabase import service_client

# Vigencia de los enlaces que recibe la app. Una hora alcanza de
# sobra para ver el diagnóstico y basta para que un enlace filtrado
# deje de servir pronto.
_VIGENCIA_SEGUNDOS = 3600


def subir(ruta: str, contenido: bytes) -> str:
    
    service_client().storage.from_(settings.storage_bucket).upload(
        path=ruta,
        file=contenido,
        file_options={"content-type": "image/jpeg", "upsert": "true"},
    )
    return ruta


def firmar(ruta: str | None) -> str | None:
    
    if not ruta:
        return None
    try:
        respuesta = service_client().storage.from_(
            settings.storage_bucket
        ).create_signed_url(ruta, _VIGENCIA_SEGUNDOS)
    except Exception:  # noqa: BLE001
        return None
    return respuesta.get("signedURL") or respuesta.get("signedUrl")


def firmar_varias(rutas: list[str]) -> dict[str, str]:
    
    limpias = [r for r in rutas if r]
    if not limpias:
        return {}

    try:
        respuestas = service_client().storage.from_(
            settings.storage_bucket
        ).create_signed_urls(limpias, _VIGENCIA_SEGUNDOS)
    except Exception:  # noqa: BLE001
        return {}

    return {
        item["path"]: item.get("signedURL") or item.get("signedUrl")
        for item in respuestas
        if item.get("path") and not item.get("error")
    }