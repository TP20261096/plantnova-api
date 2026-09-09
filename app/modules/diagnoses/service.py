import uuid

from fastapi import HTTPException, status

from app.core.security import CurrentUser
from app.core.supabase import user_client
from app.modules.diagnoses import repository as repo
from app.modules.diagnoses import storage
from app.modules.diagnoses.inference import (
    UMBRAL_CONFIANZA,
    Inferencia,
    analizar,
)
from app.modules.diagnoses.schemas import (
    DiagnosticoOut,
    PrediccionOut,
    RecetaOut,
)
from app.modules.activities.service import generar_plan_tratamiento
from app.modules.plants import repository as plants_repo
from app.modules.plants.service import recalcular_estado, recalcular_riego

TIPOS_PERMITIDOS = {"image/jpeg", "image/png", "image/webp"}
TAMANO_MAXIMO = 10 * 1024 * 1024

_NO_ENCONTRADO = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail="El diagnóstico no existe",
)


def validar_archivo(content_type: str | None, contenido: bytes) -> None:
    
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


def _guardar_imagenes(
    user_id: str, diagnostico_id: str, resultado: Inferencia
) -> tuple[str, str]:
    
    base = f"{user_id}/{diagnostico_id}"
    return (
        storage.subir(f"{base}/original.jpg", resultado.original_jpg),
        storage.subir(f"{base}/gradcam.jpg", resultado.gradcam_jpg),
    )


def _componer(
    fila: dict, ficha: dict, confianza_baja: bool, top3: list[dict]
) -> DiagnosticoOut:
    
    especie = ficha.get("species") or {}
    tratamientos = [
        RecetaOut(
            nombre=t["recetas"]["nombre"],
            descripcion=t["recetas"].get("descripcion"),
            ingredientes=t["recetas"].get("ingredientes") or [],
            preparacion=t["recetas"].get("preparacion") or [],
            modo_uso=t["recetas"].get("modo_uso"),
            precauciones=t["recetas"].get("precauciones"),
            costo_aprox=t["recetas"].get("costo_aprox"),
            frecuencia_dias=t["frecuencia_dias"],
            num_aplicaciones=t["num_aplicaciones"],
            nota=t.get("nota"),
        )
        for t in (ficha.get("disease_treatments") or [])
        if t.get("recetas")
    ]

    return DiagnosticoOut(
        id=fila["id"],
        plant_id=fila.get("plant_id"),
        estado=fila["estado"],
        cultivo=especie.get("nombre_comun"),
        especie_slug=especie.get("slug"),
        nombre_enfermedad=ficha["nombre_enfermedad"],
        nombre_cientifico=ficha.get("nombre_cientifico"),
        confianza=fila["confianza"],
        confianza_baja=confianza_baja,
        especie_confirmada=fila.get("especie_confirmada", False),
        urgencia=ficha["urgencia"],
        top3=[PrediccionOut(**p) for p in top3],
        descripcion=ficha.get("descripcion"),
        sintomas=ficha.get("sintomas"),
        causas=ficha.get("causas"),
        prevencion=ficha.get("prevencion"),
        riego_frecuencia_dias=ficha.get("riego_frecuencia_dias"),
        riego_nota=ficha.get("riego_nota"),
        otros_cuidados=ficha.get("otros_cuidados"),
        tratamientos=tratamientos,
        insumos_no_caseros=ficha.get("insumos_no_caseros") or [],
        imagen_url=storage.firmar(fila["imagen_url"]),
        gradcam_url=storage.firmar(fila.get("gradcam_url")),
        created_at=fila["created_at"],
    )


def diagnosticar(
    usuario: CurrentUser,
    contenido: bytes,
    content_type: str | None,
    plant_id: str | None = None,
) -> DiagnosticoOut:
    
    validar_archivo(content_type, contenido)
    cliente = user_client(usuario.token)

    planta = None
    if plant_id:
        planta = plants_repo.obtener(cliente, plant_id)
        if planta is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="La planta no existe",
            )

    try:
        resultado = analizar(contenido)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    principal = resultado.principal
    ficha = repo.buscar_ficha(cliente, principal.clase_raw)
    if ficha is None:
        # Ocurre si el catálogo y el orden de CLASS_NAMES divergen.
        # Es un error de configuración, no del usuario.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                f"La clase '{principal.clase_raw}' no está en el "
                "catálogo de enfermedades"
            ),
        )

    diagnostico_id = str(uuid.uuid4())
    ruta_imagen, ruta_gradcam = _guardar_imagenes(
        usuario.id, diagnostico_id, resultado
    )

    nombres = repo.nombres_por_clase(
        cliente, [p.clase_raw for p in resultado.top]
    )
    top3 = [
        {
            "clase_raw": p.clase_raw,
            "nombre_enfermedad": nombres.get(p.clase_raw),
            "confianza": p.confianza,
        }
        for p in resultado.top
    ]

    fila = repo.crear(
        cliente,
        {
            "id": diagnostico_id,
            "user_id": usuario.id,
            "plant_id": plant_id,
            "disease_id": ficha["id"],
            "clase_raw": principal.clase_raw,
            "estado": ficha["estado"],
            "confianza": principal.confianza,
            "top3": top3,
            "imagen_url": ruta_imagen,
            "gradcam_url": ruta_gradcam,
            "especie_confirmada": (
                _especies_coinciden(planta, ficha) if planta else False
            ),
        },
    )

    if plant_id and planta:
        _actualizar_planta(
            cliente, usuario.id, plant_id, planta, fila, ficha
        )

    return _componer(fila, ficha, resultado.confianza_baja, top3)


def _especies_coinciden(planta: dict, ficha: dict) -> bool:
    
    especie_planta = planta.get("species_id")
    especie_ficha = ficha.get("species_id")
    return bool(
        especie_planta
        and especie_ficha
        and especie_planta == especie_ficha
    )


def _actualizar_planta(
    cliente,
    user_id: str,
    plant_id: str,
    planta: dict,
    fila: dict,
    ficha: dict,
) -> None:
    
    generar_plan_tratamiento(
        cliente=cliente,
        user_id=user_id,
        plant_id=plant_id,
        diagnosis_id=fila["id"],
        disease_id=ficha["id"],
        estado_diagnostico=fila["estado"],
        apodo=planta.get("apodo", ""),
    )
    recalcular_estado(cliente, plant_id)
    recalcular_riego(cliente, plant_id)


def vincular(
    usuario: CurrentUser, diagnostico_id: str, plant_id: str
) -> DiagnosticoOut:
    
    cliente = user_client(usuario.token)

    fila = repo.obtener(cliente, diagnostico_id)
    if fila is None:
        raise _NO_ENCONTRADO
    if fila.get("plant_id") and fila["plant_id"] != plant_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El diagnóstico ya pertenece a otra planta",
        )
    planta = plants_repo.obtener(cliente, plant_id)
    if planta is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La planta no existe",
        )

    ficha = repo.buscar_ficha(cliente, fila["clase_raw"])

    fila = repo.actualizar(
        cliente,
        diagnostico_id,
        {
            "plant_id": plant_id,
            "especie_confirmada": _especies_coinciden(planta, ficha),
        },
    )
    _actualizar_planta(
        cliente, usuario.id, plant_id, planta, fila, ficha
    )

    baja = fila["confianza"] < UMBRAL_CONFIANZA
    return _componer(fila, ficha, baja, fila.get("top3") or [])


def obtener_diagnostico(
    usuario: CurrentUser, diagnostico_id: str
) -> DiagnosticoOut:
    
    cliente = user_client(usuario.token)
    fila = repo.obtener(cliente, diagnostico_id)
    if fila is None:
        raise _NO_ENCONTRADO

    ficha = repo.buscar_ficha(cliente, fila["clase_raw"])
    baja = fila["confianza"] < UMBRAL_CONFIANZA
    return _componer(fila, ficha, baja, fila.get("top3") or [])