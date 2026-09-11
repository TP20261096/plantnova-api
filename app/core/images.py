import io

from fastapi import HTTPException, status
from PIL import Image, UnidentifiedImageError

TIPOS_PERMITIDOS = {"image/jpeg", "image/png", "image/webp"}
TAMANO_MAXIMO = 10 * 1024 * 1024

# Lado máximo de las fotos del jardín. Una foto de celular ronda los
# 4000 px; guardarla completa desperdicia almacenamiento y ancho de
# banda para mostrarse en una tarjeta de pocos centímetros.
LADO_MAXIMO = 1024
CALIDAD_JPEG = 85


def validar_imagen(content_type: str | None, contenido: bytes) -> None:
    
    if not contenido:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo está vacío",
        )
    if content_type not in TIPOS_PERMITIDOS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Formato no admitido. Usa JPEG, PNG o WEBP",
        )
    if len(contenido) > TAMANO_MAXIMO:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="La imagen supera los 10 MB",
        )


def a_jpeg(contenido: bytes) -> bytes:
    
    try:
        imagen = Image.open(io.BytesIO(contenido)).convert("RGB")
    except (UnidentifiedImageError, OSError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo no es una imagen válida",
        ) from exc

    imagen.thumbnail((LADO_MAXIMO, LADO_MAXIMO))

    buffer = io.BytesIO()
    imagen.save(buffer, format="JPEG", quality=CALIDAD_JPEG)
    return buffer.getvalue()