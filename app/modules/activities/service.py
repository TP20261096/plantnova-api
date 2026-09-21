from datetime import date, datetime, timedelta, timezone
import math

from fastapi import HTTPException, status
from supabase import Client

from app.core.security import CurrentUser
from app.core.supabase import user_client
from app.modules.activities import repository as repo
from app.modules.activities.schemas import (
    ActividadCreate,
    ActividadOut,
    ActividadUpdate,
)
from app.modules.plants import repository as plants_repo
from app.modules.plants.service import recalcular_estado, recalcular_riego

PERU_TZ = timezone(timedelta(hours=-5))

_NO_ENCONTRADA = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail="La actividad no existe",
)

_DIAS_HASTA_REVISION = 1


def _a_salida(fila: dict, dia: date) -> ActividadOut:
    planta = fila.get("plants") or {}
    receta = fila.get("recetas") or {}
    programada = date.fromisoformat(fila["fecha_programada"])

    return ActividadOut(
        id=fila["id"],
        plant_id=fila["plant_id"],
        planta=planta.get("apodo"),
        tipo=fila["tipo"],
        estado=fila["estado"],
        titulo=fila["titulo"],
        descripcion=fila.get("descripcion"),
        fecha_programada=programada,
        fecha_completada=fila.get("fecha_completada"),
        dias_atraso=max(0, (dia - programada).days),
        aplicacion_num=fila.get("aplicacion_num"),
        total_aplicaciones=fila.get("total_aplicaciones"),
        receta_nombre=receta.get("nombre"),
        diagnosis_id=fila.get("diagnosis_id"),
    )


def _fecha_proximo_riego(planta: dict) -> date | None:
    frecuencia = planta.get("riego_frecuencia_dias")
    if not frecuencia:
        return None

    referencia = planta.get("ultimo_riego") or planta["created_at"][:10]
    return date.fromisoformat(referencia) + timedelta(days=frecuencia)


def _materializar_riegos(
    cliente: Client, user_id: str, dia: date
) -> None:
    for planta in plants_repo.listar(cliente, user_id):
        proximo = _fecha_proximo_riego(planta)
        if proximo is None or proximo > dia:
            continue
        if repo.pendiente_de_tipo(cliente, planta["id"], "Riego"):
            continue

        repo.crear(
            cliente,
            {
                "user_id": user_id,
                "plant_id": planta["id"],
                "tipo": "Riego",
                "titulo": f"Regar {planta['apodo']}",
                "descripcion": "Riega en la base, evitando mojar el follaje.",
                "fecha_programada": proximo.isoformat(),
            },
        )


def _proyectar_riegos(
    cliente: Client, user_id: str, dia: date
) -> list[ActividadOut]:
    proyectadas = []
    for planta in plants_repo.listar(cliente, user_id):
        if repo.pendiente_de_tipo(cliente, planta["id"], "Riego"):
            continue
        if _fecha_proximo_riego(planta) != dia:
            continue

        proyectadas.append(
            ActividadOut(
                id=None,
                plant_id=planta["id"],
                planta=planta["apodo"],
                tipo="Riego",
                estado="Pendiente",
                titulo=f"Regar {planta['apodo']}",
                descripcion=None,
                fecha_programada=dia,
                fecha_completada=None,
                dias_atraso=0,
                aplicacion_num=None,
                total_aplicaciones=None,
                receta_nombre=None,
                diagnosis_id=None,
                proyectada=True,
            )
        )
    return proyectadas


def listar_agenda(
    usuario: CurrentUser, dia: date | None = None
) -> list[ActividadOut]:
    hoy_peru = datetime.now(PERU_TZ).date()
    dia = dia or hoy_peru
    cliente = user_client(usuario.token)

    if dia > hoy_peru:
        reales = [
            _a_salida(f, dia)
            for f in repo.programadas_desde(cliente, usuario.id, dia)
        ]
        return reales + _proyectar_riegos(cliente, usuario.id, dia)

    _materializar_riegos(cliente, usuario.id, dia)
    actividades = [
        _a_salida(f, dia)
        for f in repo.agenda(cliente, usuario.id, dia)
    ]
    actividades.sort(
        key=lambda a: (-a.dias_atraso, a.tipo, a.fecha_programada)
    )
    return actividades


def generar_plan_tratamiento(
    cliente: Client,
    user_id: str,
    plant_id: str,
    diagnosis_id: str,
    disease_id: str,
    estado_diagnostico: str,
    apodo: str,
    tratamiento_prioritario: dict | None = None,
) -> None:
    repo.cancelar_pendientes(
        cliente, plant_id, ["Tratamiento", "Revision"]
    )

    if estado_diagnostico == "Sana":
        return

    plan = tratamiento_prioritario or repo.tratamiento_de_enfermedad(cliente, disease_id)
    if plan is None:
        return

    receta = plan.get("recetas") or {}
    frecuencia = plan.get("frecuencia_dias")
    num_aplicaciones = plan.get("num_aplicaciones")
    receta_id = plan.get("receta_id") or receta.get("id")

    tiene_secuencia = (frecuencia is not None) or (num_aplicaciones is not None)
    aplicacion_inicial = 1 if tiene_secuencia else None

    repo.crear(
        cliente,
        {
            "user_id": user_id,
            "plant_id": plant_id,
            "diagnosis_id": diagnosis_id,
            "receta_id": receta_id,
            "tipo": "Tratamiento",
            "titulo": f"Aplicar {receta.get('nombre', 'tratamiento')}",
            "descripcion": plan.get("nota") or receta.get("modo_uso"),
            "fecha_programada": datetime.now(PERU_TZ).date().isoformat(),
            "aplicacion_num": aplicacion_inicial,
            "total_aplicaciones": num_aplicaciones,
        },
    )


def _encadenar_siguiente(cliente: Client, fila: dict) -> None:
    completada = date.fromisoformat(fila["fecha_completada"])
    tipo = fila["tipo"]

    if tipo == "Riego":
        plants_repo.actualizar(
            cliente,
            fila["plant_id"],
            {"ultimo_riego": fila["fecha_completada"]},
        )
        recalcular_riego(cliente, fila["plant_id"])
        return

    if tipo != "Tratamiento":
        return

    actual = fila.get("aplicacion_num")
    total = fila.get("total_aplicaciones")

    plan = repo.tratamiento_de_enfermedad(
        cliente, _disease_id_de(cliente, fila)
    )
    frecuencia = plan.get("frecuencia_dias") if plan else None

    if not frecuencia and not total:
        repo.crear(
            cliente,
            {
                "user_id": fila["user_id"],
                "plant_id": fila["plant_id"],
                "diagnosis_id": fila.get("diagnosis_id"),
                "tipo": "Revision",
                "titulo": "Revisar la planta con una nueva captura",
                "descripcion": "Aplicación única completada. Revisa la evolución.",
                "fecha_programada": (
                    completada + timedelta(days=_DIAS_HASTA_REVISION)
                ).isoformat(),
            },
        )
        return

    if frecuencia and total is None:
        repo.crear(
            cliente,
            {
                "user_id": fila["user_id"],
                "plant_id": fila["plant_id"],
                "diagnosis_id": fila.get("diagnosis_id"),
                "receta_id": fila.get("receta_id"),
                "tipo": "Tratamiento",
                "titulo": fila["titulo"],
                "descripcion": fila.get("descripcion"),
                "fecha_programada": (
                    completada + timedelta(days=frecuencia)
                ).isoformat(),
                "aplicacion_num": (actual or 1) + 1,
                "total_aplicaciones": None,
            },
        )
        return

    if total is not None and actual is not None and actual >= total:
        repo.crear(
            cliente,
            {
                "user_id": fila["user_id"],
                "plant_id": fila["plant_id"],
                "diagnosis_id": fila.get("diagnosis_id"),
                "tipo": "Revision",
                "titulo": "Revisar la planta con una nueva captura",
                "descripcion": "Terminó el tratamiento. Toma una foto para evaluar la evolución.",
                "fecha_programada": (
                    completada + timedelta(days=_DIAS_HASTA_REVISION)
                ).isoformat(),
            },
        )
        return

    repo.crear(
        cliente,
        {
            "user_id": fila["user_id"],
            "plant_id": fila["plant_id"],
            "diagnosis_id": fila.get("diagnosis_id"),
            "receta_id": fila.get("receta_id"),
            "tipo": "Tratamiento",
            "titulo": fila["titulo"],
            "descripcion": fila.get("descripcion"),
            "fecha_programada": (
                completada + timedelta(days=frecuencia)
            ).isoformat(),
            "aplicacion_num": (actual or 1) + 1,
            "total_aplicaciones": total,
        },
    )


def _disease_id_de(cliente: Client, fila: dict) -> str | None:
    if not fila.get("diagnosis_id"):
        return None

    respuesta = (
        cliente.table("diagnoses")
        .select("disease_id")
        .eq("id", fila["diagnosis_id"])
        .limit(1)
        .execute()
    )
    return respuesta.data[0]["disease_id"] if respuesta.data else None


def crear_actividad(
    usuario: CurrentUser, datos: ActividadCreate
) -> ActividadOut:
    cliente = user_client(usuario.token)
    if plants_repo.obtener(cliente, datos.plant_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La planta no existe",
        )
    if repo.pendiente_de_tipo(cliente, datos.plant_id, datos.tipo):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"La planta ya tiene una tarea de {datos.tipo} "
                "pendiente"
            ),
        )

    fila = datos.model_dump(mode="json")
    fila["user_id"] = usuario.id
    creada = repo.crear(cliente, fila)
    return _a_salida(
        repo.obtener(cliente, creada["id"]), datetime.now(PERU_TZ).date()
    )


def actualizar_actividad(
    usuario: CurrentUser, actividad_id: str, cambios: ActividadUpdate
) -> ActividadOut:
    cliente = user_client(usuario.token)
    fila = repo.obtener(cliente, actividad_id)
    if fila is None:
        raise _NO_ENCONTRADA

    valores = cambios.model_dump(mode="json", exclude_unset=True)
    if not valores:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se envió ningún campo para actualizar",
        )

    completa = valores.get("estado") == "Completada"
    if completa:
        if fila["estado"] == "Completada":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="La actividad ya estaba completada",
            )
        valores["fecha_completada"] = datetime.now(PERU_TZ).date().isoformat()
    elif valores.get("estado") == "Cancelada":
        valores["fecha_completada"] = datetime.now(PERU_TZ).date().isoformat()

    actualizada = repo.actualizar(cliente, actividad_id, valores)

    if completa:
        _encadenar_siguiente(cliente, actualizada)
        recalcular_estado(cliente, fila["plant_id"])

    return _a_salida(
        repo.obtener(cliente, actividad_id), datetime.now(PERU_TZ).date()
    )


def eliminar_actividad(
    usuario: CurrentUser, actividad_id: str
) -> None:
    cliente = user_client(usuario.token)
    if repo.obtener(cliente, actividad_id) is None:
        raise _NO_ENCONTRADA
    repo.eliminar(cliente, actividad_id)