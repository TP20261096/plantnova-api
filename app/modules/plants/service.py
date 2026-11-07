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
    RecetaOut
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


def _indexar_seguimiento(actividades: list[dict], hoy: date) -> dict[str, tuple[date, int, str]]:
    """
    Decide, por planta, qué tarea de seguimiento mostrar.
    Respeta el mismo orden de preferencia que antes se resolvía en
    tres viajes a la base: primero una revisión pendiente, luego una
    aplicación pendiente y, en último lugar, la revisión completada.
    Entre varias candidatas del mismo rango gana la más próxima.
    """
    mejor: dict[str, tuple[int, date, str]] = {}

    for act in actividades:
        tipo, estado = act["tipo"], act["estado"]
        if tipo == "Revision" and estado == "Pendiente":
            rango, campo, etiqueta = 0, "fecha_programada", "Revision"
        elif tipo == "Tratamiento" and estado == "Pendiente":
            rango, campo, etiqueta = (
                1, "fecha_programada", "Tratamiento",
            )
        elif tipo == "Revision":
            rango, campo, etiqueta = (
                2, "fecha_completada", "RevisionCompletada",
            )
        else:
            continue

        crudo = act.get(campo)
        if not crudo:
            continue

        fecha = date.fromisoformat(str(crudo)[:10])
        actual = mejor.get(act["plant_id"])
        if actual is None or (rango, fecha) < (actual[0], actual[1]):
            mejor[act["plant_id"]] = (rango, fecha, etiqueta)

    return {
        pid: (fecha, (fecha - hoy).days, etiqueta)
        for pid, (_, fecha, etiqueta) in mejor.items()
    }


def _seguimiento_de(cliente: Client, user_id: str) -> dict:
    return _indexar_seguimiento(
        repo.actividades_de_seguimiento(cliente, user_id),
        datetime.now(PERU_TZ).date(),
    )

def _a_resumen(planta: dict,
    seguimiento: tuple[date, int, str] | None = None,) -> PlantaResumen:
    proximo, faltan = _proximo_riego(planta)
    prox_trat, faltan_trat, tipo_prox = seguimiento or (None, None, None)
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
    
def _distrito_de(cliente: Client, user_id: str) -> str | None:
    """Lee el distrito del perfil, que fija el punto del clima.

    Args:
        cliente: Cliente Supabase del usuario.
        user_id: UUID del dueño de la planta.

    Returns:
        Nombre del distrito, o None si el usuario no eligió ninguno.
    """
    perfil = (
        cliente.table("profiles")
        .select("distrito")
        .eq("id", user_id)
        .limit(1)
        .execute()
    )
    return perfil.data[0]["distrito"] if perfil.data else None


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
        obtener_clima(distrito=_distrito_de(cliente, planta["user_id"])),
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
        base,
        datos.ubicacion,
        obtener_clima(distrito=_distrito_de(cliente, usuario.id)),
    )

    creada = repo.crear(cliente, fila)
    completa = repo.obtener(cliente, creada["id"])
    return _a_resumen(completa)


def listar_plantas(
    usuario: CurrentUser, estado: str | None = None
) -> list[PlantaResumen]:
    
    cliente = user_client(usuario.token)
    seguimiento = _seguimiento_de(cliente, usuario.id)
    return [
        _a_resumen(p, seguimiento.get(p["id"]))
        for p in repo.listar(cliente, usuario.id, estado)
    ]


def obtener_planta(usuario: CurrentUser, planta_id: str) -> PlantaDetalle:
    cliente = user_client(usuario.token)
    planta = repo.obtener(cliente, planta_id)
    if planta is None:
        raise _NO_ENCONTRADA

    diagnosticos = repo.historial(cliente, planta_id)
    ultimo = diagnosticos[0] if diagnosticos else None
    catalogo = (ultimo or {}).get("disease_catalog") or {}

    firmadas = firmar_varias([d["imagen_url"] for d in diagnosticos])

    resumen = _a_resumen(
        planta, _seguimiento_de(cliente, planta["user_id"]).get(planta_id)
    )
    
    tratamientos = []
    if ultimo and ultimo.get("disease_id"):
        tratamientos = [
            RecetaOut(
                nombre=t["recetas"]["nombre"],
                descripcion=t["recetas"].get("descripcion"),
                ingredientes=t["recetas"].get("ingredientes") or [],
                preparacion=t["recetas"].get("preparacion") or [],
                modo_uso=t["recetas"].get("modo_uso"),
                precauciones=t["recetas"].get("precauciones"),
                costo_aprox=t["recetas"].get("costo_aprox"),
                fuentes=t["recetas"].get("fuentes") or [],
                frecuencia_dias=t.get("frecuencia_dias"),
                num_aplicaciones=t.get("num_aplicaciones"),
                nota=t.get("nota"),
            )
            for t in repo.tratamientos_de(
                cliente, ultimo["disease_id"]
            )
            if t.get("recetas")
        ]
        
    return PlantaDetalle(
        **resumen.model_dump(),
        species_id=planta.get("species_id"),
        fecha_siembra=planta.get("fecha_siembra"),
        riego_nota=catalogo.get("riego_nota"),
        otros_cuidados=catalogo.get("otros_cuidados"),
        tratamientos=tratamientos,
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

    return _a_resumen(
        repo.obtener(cliente, planta_id),
        _seguimiento_de(cliente, usuario.id).get(planta_id),
    )


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