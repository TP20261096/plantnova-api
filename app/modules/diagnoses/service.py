import uuid

from fastapi import HTTPException, status

from app.core import storage
from datetime import date, datetime, timedelta, timezone
import math

PERU_TZ = timezone(timedelta(hours=-5))

from app.core.images import validar_imagen
from app.core.security import CurrentUser
from app.core.supabase import user_client
from app.modules.activities.service import generar_plan_tratamiento
from app.modules.diagnoses import repository as repo
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
from app.modules.plants import repository as plants_repo
from app.modules.plants.service import recalcular_estado, recalcular_riego
from app.modules.activities import repository as activities_repo


_NO_ENCONTRADO = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail="El diagnóstico no existe",
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

    # El primero de la lista es el prioritario. El orden lo fija la
    # columna prioridad del catálogo, no el código.
    ordenados = sorted(
        (
            t
            for t in (ficha.get("disease_treatments") or [])
            if t.get("recetas")
        ),
        key=lambda t: (
            t["prioridad"] if t.get("prioridad") is not None else 9,
            t.get("frecuencia_dias") or 99,
        ),
    )

    tratamientos = [
        RecetaOut(
            nombre=t["recetas"]["nombre"],
            descripcion=t["recetas"].get("descripcion"),
            ingredientes=t["recetas"].get("ingredientes") or [],
            preparacion=t["recetas"].get("preparacion") or [],
            modo_uso=t["recetas"].get("modo_uso"),
            precauciones=t["recetas"].get("precauciones"),
            costo_aprox=(
                None
                if t["recetas"].get("costo_aprox") in (None, "", "null")
                else t["recetas"].get("costo_aprox")
            ),
            fuentes=t["recetas"].get("fuentes") or [],
            frecuencia_dias=t.get("frecuencia_dias"),
            num_aplicaciones=t.get("num_aplicaciones"),
            nota=t.get("nota"),
        )
        for t in ordenados
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
    validar_imagen(content_type, contenido)
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
    if resultado.confianza_baja:
        plant_id, planta = None, None

    principal = resultado.principal
    ficha = repo.buscar_ficha(cliente, principal.clase_raw)
    if ficha is None:
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
        planta = _heredar_del_diagnostico(
            cliente, plant_id, planta, fila, ficha
        )
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

def _heredar_del_diagnostico(
    cliente,
    plant_id: str,
    planta: dict,
    fila: dict,
    ficha: dict,
) -> dict:
    """Completa la planta con lo que el diagnóstico ya averiguó.

    Solo rellena huecos: si el usuario eligió especie o subió foto,
    lo suyo manda sobre lo que dedujo el modelo.

    Args:
        cliente: Cliente Supabase del usuario.
        plant_id: UUID de la planta.
        planta: Fila de plants antes de completar.
        fila: Diagnóstico recién guardado.
        ficha: Enfermedad detectada.

    Returns:
        La planta, actualizada si hubo algo que heredar.
    """
    cambios = {}
    if not planta.get("species_id") and ficha.get("species_id"):
        cambios["species_id"] = ficha["species_id"]
    if not planta.get("foto_url") and fila.get("imagen_url"):
        cambios["foto_url"] = fila["imagen_url"]

    if not cambios:
        return planta
    return plants_repo.actualizar(cliente, plant_id, cambios)

def _actualizar_planta(
    cliente,
    user_id: str,
    plant_id: str,
    planta: dict,
    fila: dict,
    ficha: dict,
) -> None:
    estado_diag = (fila.get("estado") or ficha.get("estado") or "").lower()
    
    # 1. Buscar si la planta tenía una tarea de tipo "Revision" pendiente y completarla
    revision_pendiente = cliente.table("activities").select("id").eq("plant_id", plant_id).eq("tipo", "Revision").eq("estado", "Pendiente").execute()
    if revision_pendiente.data:
        for rev in revision_pendiente.data:
            cliente.table("activities").update({
                "estado": "Completada",
                "fecha_completada": datetime.now(PERU_TZ).date().isoformat()
            }).eq("id", rev["id"]).execute()

    # 2. Si la planta está sana, cancelamos el tratamiento en curso
    if "sana" in estado_diag or "saludable" in estado_diag:
        activities_repo.cancelar_pendientes(
            cliente, plant_id, ["Tratamiento", "Revision"]
        )
    else:
        generar_plan_tratamiento(
            cliente=cliente,
            user_id=user_id,
            plant_id=plant_id,
            diagnosis_id=fila["id"],
            disease_id=ficha["id"],
            estado_diagnostico=fila["estado"],
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
    
    if fila["confianza"] < UMBRAL_CONFIANZA:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "El diagnóstico no alcanza la confianza mínima para "
                "guardarse. Toma la foto de nuevo."
            ),
        )
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

    coincide = _especies_coinciden(planta, ficha)
    planta = _heredar_del_diagnostico(
        cliente, plant_id, planta, fila, ficha
    )

    fila = repo.actualizar(
        cliente,
        diagnostico_id,
        {"plant_id": plant_id, "especie_confirmada": coincide},
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