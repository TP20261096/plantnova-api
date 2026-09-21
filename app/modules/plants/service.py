from datetime import date, datetime, timedelta, timezone

from fastapi import HTTPException, status
from supabase import Client

from app.core.clima import obtener_clima
from app.core.images import a_jpeg, validar_imagen
from app.core.security import CurrentUser
from app.core.storage import firmar, firmar_varias, subir
from app.core.supabase import user_client
from app.modules.plants import repository as repo
from app.modules.plants.riego import calcular_frecuencia
from app.modules.plants.schemas import (
    DiagnosticoResumen,
    PlantaCreate,
    PlantaDetalle,
    PlantaResumen,
    PlantaUpdate,
)

PERU_TZ = timezone(timedelta(hours=-5))

_NO_ENCONTRADA = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail="La planta no existe",
)


def _base_dias(planta: dict, ultimo_diagnostico: dict | None) -> int | None:
    if ultimo_diagnostico:
        catalogo = ultimo_diagnostico.get("disease_catalog") or {}
        if catalogo.get("riego_frecuencia_dias"):
            return catalogo["riego_frecuencia_dias"]

    especie = planta.get("species") or {}
    return especie.get("riego_base_dias")


def _proximo_riego(planta: dict) -> tuple[date | None, int | None]:
    frecuencia = planta.get("riego_frecuencia_dias")
    if not frecuencia:
        return None, None

    referencia = planta.get("ultimo_riego")
    if referencia:
        base = date.fromisoformat(str(referencia)[:10])
    else:
        base = date.fromisoformat(str(planta["created_at"])[:10])

    proximo = base + timedelta(days=frecuencia)
    hoy_peru = datetime.now(PERU_TZ).date()
    faltan = (proximo - hoy_peru).days
    return proximo, faltan


def _proximo_tratamiento(cliente: Client, planta_id: str) -> tuple[date | None, int | None, str | None]:
    # 1. Buscamos primero si hay alguna actividad de tipo 'Revision' en estado 'Pendiente'
    revision_pendiente = (
        cliente.table("activities")
        .select("*")
        .eq("plant_id", planta_id)
        .eq("tipo", "Revision")
        .eq("estado", "Pendiente")
        .order("fecha_programada", desc=False)
        .limit(1)
        .execute()
    )
    
    if revision_pendiente.data:
        actividad = revision_pendiente.data[0]
        tipo_actividad = "Revision"
    else:
        # 2. Si no hay revisión pendiente, buscamos un tratamiento pendiente normal usando el repositorio
        actividad = repo.proxima_actividad_tratamiento(cliente, planta_id)
        tipo_actividad = "Tratamiento"
        
        if not actividad:
            # 3. Si tampoco hay tratamiento, buscamos si la revisión ya fue completada
            revision_completada = (
                cliente.table("activities")
                .select("*")
                .eq("plant_id", planta_id)
                .eq("tipo", "Revision")
                .eq("estado", "Completada")
                .order("fecha_completada", desc=False)
                .limit(1)
                .execute()
            )
            if revision_completada.data:
                actividad = revision_completada.data[0]
                tipo_actividad = "RevisionCompletada"
            else:
                return None, None, None

    fecha_str = actividad.get("fecha_completada") if tipo_actividad == "RevisionCompletada" else actividad.get("fecha_programada")
    if not fecha_str:
        return None, None, None

    fecha_dt = date.fromisoformat(str(fecha_str)[:10])
    hoy_peru = datetime.now(PERU_TZ).date()
    faltan = (fecha_dt - hoy_peru).days
    
    return fecha_dt, faltan, tipo_actividad


def _a_resumen(cliente: Client, planta: dict) -> PlantaResumen:
    proximo, faltan = _proximo_riego(planta)
    prox_trat, faltan_trat, tipo_prox = _proximo_tratamiento(cliente, planta["id"])
    especie = planta.get("species") or {}

    ultimo = None
    if planta.get("ultimo_riego"):
        ultimo = date.fromisoformat(str(planta["ultimo_riego"])[:10])

    return PlantaResumen(
        id=planta["id"],
        apodo=planta["apodo"],
        especie=especie.get("nombre_comun"),
        ubicacion=planta["ubicacion"],
        etapa=planta["etapa"],
        estado=planta["estado"],
        foto_url=firmar(planta.get("foto_url")),
        riego_frecuencia_dias=planta.get("riego_frecuencia_dias"),
        ultimo_riego=ultimo,
        proximo_riego=proximo,
        dias_para_riego=faltan,
        proximo_tratamiento=prox_trat,
        dias_para_tratamiento=faltan_trat,
        proximo_tipo=tipo_prox,  # <--- Envía el tipo correcto al front
    )


def recalcular_estado(cliente: Client, planta_id: str) -> str:
    diagnosticos = repo.historial(cliente, planta_id)

    if not diagnosticos:
        estado = "Sin_diagnostico"
    elif repo.tiene_tratamiento_pendiente(cliente, planta_id):
        estado = "En_tratamiento"
    elif diagnosticos[0]["estado"] == "Sana":
        estado = "Sana"
    else:
        estado = "En_tratamiento"

    repo.actualizar(cliente, planta_id, {"estado": estado})
    return estado


def recalcular_riego(cliente: Client, planta_id: str) -> int | None:
    planta = repo.obtener(cliente, planta_id)
    if planta is None:
        raise _NO_ENCONTRADA

    diagnosticos = repo.historial(cliente, planta_id)
    frecuencia = calcular_frecuencia(
        _base_dias(planta, diagnosticos[0] if diagnosticos else None),
        planta["ubicacion"],
        obtener_clima(),
    )

    repo.actualizar(
        cliente, planta_id, {"riego_frecuencia_dias": frecuencia}
    )
    return frecuencia


def crear_planta(
    usuario: CurrentUser, datos: PlantaCreate
) -> PlantaResumen:
    cliente = user_client(usuario.token)

    base = None
    if datos.species_id:
        especie = (
            cliente.table("species")
            .select("riego_base_dias")
            .eq("id", datos.species_id)
            .limit(1)
            .execute()
        )
        if not especie.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La especie indicada no existe",
            )
        base = especie.data[0]["riego_base_dias"]

    fila = datos.model_dump(mode="json", exclude_none=True)
    fila["user_id"] = usuario.id
    fila["riego_frecuencia_dias"] = calcular_frecuencia(
        base, datos.ubicacion, obtener_clima()
    )

    creada = repo.crear(cliente, fila)
    completa = repo.obtener(cliente, creada["id"])
    return _a_resumen(cliente, completa)


def listar_plantas(usuario: CurrentUser) -> list[PlantaResumen]:
    cliente = user_client(usuario.token)
    return [_a_resumen(cliente, p) for p in repo.listar(cliente, usuario.id)]


def obtener_planta(usuario: CurrentUser, planta_id: str) -> PlantaDetalle:
    cliente = user_client(usuario.token)
    planta = repo.obtener(cliente, planta_id)
    if planta is None:
        raise _NO_ENCONTRADA

    diagnosticos = repo.historial(cliente, planta_id)
    ultimo = diagnosticos[0] if diagnosticos else None
    catalogo = (ultimo or {}).get("disease_catalog") or {}

    firmadas = firmar_varias([d["imagen_url"] for d in diagnosticos])

    resumen = _a_resumen(cliente, planta)
    return PlantaDetalle(
        **resumen.model_dump(),
        species_id=planta.get("species_id"),
        fecha_siembra=planta.get("fecha_siembra"),
        riego_nota=catalogo.get("riego_nota"),
        otros_cuidados=catalogo.get("otros_cuidados"),
        created_at=planta["created_at"],
        diagnosticos=[
            DiagnosticoResumen(
                id=d["id"],
                nombre_enfermedad=(
                    (d.get("disease_catalog") or {}).get(
                        "nombre_enfermedad"
                    )
                ),
                estado=d["estado"],
                confianza=d["confianza"],
                imagen_url=firmadas.get(d["imagen_url"], ""),
                created_at=d["created_at"],
            )
            for d in diagnosticos
        ],
    )


def actualizar_planta(
    usuario: CurrentUser, planta_id: str, cambios: PlantaUpdate
) -> PlantaResumen:
    cliente = user_client(usuario.token)
    if repo.obtener(cliente, planta_id) is None:
        raise _NO_ENCONTRADA

    valores = cambios.model_dump(mode="json", exclude_unset=True)
    if not valores:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se envió ningún campo para actualizar",
        )

    repo.actualizar(cliente, planta_id, valores)

    if {"ubicacion", "species_id", "ultimo_riego"} & valores.keys():
        recalcular_riego(cliente, planta_id)

    return _a_resumen(cliente, repo.obtener(cliente, planta_id))


def eliminar_planta(usuario: CurrentUser, planta_id: str) -> None:
    cliente = user_client(usuario.token)
    if repo.obtener(cliente, planta_id) is None:
        raise _NO_ENCONTRADA
    repo.eliminar(cliente, planta_id)


def subir_foto(
    usuario: CurrentUser,
    planta_id: str,
    contenido: bytes,
    content_type: str | None,
) -> PlantaDetalle:
    cliente = user_client(usuario.token)
    if repo.obtener(cliente, planta_id) is None:
        raise _NO_ENCONTRADA

    validar_imagen(content_type, contenido)
    ruta = subir(
        f"{usuario.id}/plants/{planta_id}.jpg", a_jpeg(contenido)
    )
    repo.actualizar(cliente, planta_id, {"foto_url": ruta})

    return obtener_planta(usuario, planta_id)