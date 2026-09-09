from datetime import date, timedelta

from fastapi import HTTPException, status
from supabase import Client

from app.core.clima import obtener_clima
from app.core.security import CurrentUser
from app.core.supabase import user_client
from app.modules.diagnoses.storage import firmar_varias
from app.modules.plants import repository as repo
from app.modules.plants.riego import calcular_frecuencia
from app.modules.plants.schemas import (
    DiagnosticoResumen,
    PlantaCreate,
    PlantaDetalle,
    PlantaResumen,
    PlantaUpdate,
)

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
        base = date.fromisoformat(referencia)
    else:
        base = date.fromisoformat(planta["created_at"][:10])

    proximo = base + timedelta(days=frecuencia)
    return proximo, (proximo - date.today()).days


def _a_resumen(planta: dict) -> PlantaResumen:
    
    proximo, faltan = _proximo_riego(planta)
    especie = planta.get("species") or {}
    return PlantaResumen(
        id=planta["id"],
        apodo=planta["apodo"],
        especie=especie.get("nombre_comun"),
        ubicacion=planta["ubicacion"],
        etapa=planta["etapa"],
        estado=planta["estado"],
        foto_url=planta.get("foto_url"),
        riego_frecuencia_dias=planta.get("riego_frecuencia_dias"),
        ultimo_riego=planta.get("ultimo_riego"),
        proximo_riego=proximo,
        dias_para_riego=faltan,
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
        # Hay un diagnóstico adverso pero ya no quedan aplicaciones
        # pendientes: el ciclo terminó y corresponde revisar de nuevo.
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
    return _a_resumen(completa)


def listar_plantas(usuario: CurrentUser) -> list[PlantaResumen]:
    
    cliente = user_client(usuario.token)
    return [_a_resumen(p) for p in repo.listar(cliente, usuario.id)]


def obtener_planta(usuario: CurrentUser, planta_id: str) -> PlantaDetalle:
    
    cliente = user_client(usuario.token)
    planta = repo.obtener(cliente, planta_id)
    if planta is None:
        raise _NO_ENCONTRADA

    diagnosticos = repo.historial(cliente, planta_id)
    ultimo = diagnosticos[0] if diagnosticos else None
    catalogo = (ultimo or {}).get("disease_catalog") or {}

    # Las imagenes se guardan como rutas de un bucket privado, asi
    # que hay que firmarlas. Se hace en una sola llamada para no
    # multiplicar las peticiones a Storage.
    firmadas = firmar_varias([d["imagen_url"] for d in diagnosticos])

    resumen = _a_resumen(planta)
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

    if {"ubicacion", "species_id"} & valores.keys():
        recalcular_riego(cliente, planta_id)

    return _a_resumen(repo.obtener(cliente, planta_id))


def eliminar_planta(usuario: CurrentUser, planta_id: str) -> None:
    
    cliente = user_client(usuario.token)
    if repo.obtener(cliente, planta_id) is None:
        raise _NO_ENCONTRADA
    repo.eliminar(cliente, planta_id)