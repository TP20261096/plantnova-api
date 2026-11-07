from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

import httpx
import time

from app.core.config import settings
from app.core.supabase import service_client
from app.core.distritos import DISTRITOS, coordenadas

_API_URL = "https://api.open-meteo.com/v1/forecast"
_TIMEOUT = 6.0
PERU_TZ = timezone(timedelta(hours=-5))

# Promedios de Lima Metropolitana. De mayo a octubre domina la garúa
# y la humedad se mantiene alta; el resto del año baja con el verano.
_HUMEDAD_INVIERNO = 85.0
_HUMEDAD_VERANO = 72.0
_MESES_INVIERNO = range(5, 11)


@dataclass(frozen=True)
class Clima:
    """Condiciones agregadas de un día.

    Attributes:
        humedad_media: Humedad relativa media en porcentaje.
        precipitacion_mm: Lluvia acumulada del día en milímetros.
        temp_media: Temperatura media en grados Celsius.
        fuente: Origen del dato, open-meteo o estacional.
    """

    humedad_media: float
    precipitacion_mm: float
    temp_media: float | None
    fuente: str


def _estacional(fecha: date) -> Clima:
    """Devuelve el promedio histórico de Lima para la fecha.

    Args:
        fecha: Día consultado.

    Returns:
        Clima estimado a partir de la estación del año.
    """
    invierno = fecha.month in _MESES_INVIERNO
    return Clima(
        humedad_media=(
            _HUMEDAD_INVIERNO if invierno else _HUMEDAD_VERANO
        ),
        precipitacion_mm=0.0,
        temp_media=None,
        fuente="estacional",
    )


def _consultar_api(fecha: date, distrito: str) -> Clima | None:
    """Consulta Open-Meteo para una fecha y un distrito.

    Se piden los valores por hora y se agregan aquí, en lugar de usar
    los agregados diarios, porque los primeros están disponibles para
    todo el rango de fechas del servicio.

    Args:
        fecha: Día consultado.
        distrito: Distrito cuyo centroide se consulta.

    Returns:
        Clima observado, o None si la API falla o no trae datos.
    """
    lat, lon = coordenadas(distrito)
    parametros = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "relative_humidity_2m,precipitation,temperature_2m",
        "timezone": "America/Lima",
        "start_date": fecha.isoformat(),
        "end_date": fecha.isoformat(),
    }
    try:
        respuesta = httpx.get(
            _API_URL, params=parametros, timeout=_TIMEOUT
        )
        respuesta.raise_for_status()
        horas = respuesta.json()["hourly"]
    except (httpx.HTTPError, KeyError, ValueError):
        return None

    humedades = [h for h in horas["relative_humidity_2m"] if h is not None]
    lluvias = [p for p in horas["precipitation"] if p is not None]
    temps = [t for t in horas["temperature_2m"] if t is not None]
    if not humedades:
        return None

    return Clima(
        humedad_media=round(sum(humedades) / len(humedades), 2),
        precipitacion_mm=round(sum(lluvias), 2),
        temp_media=round(sum(temps) / len(temps), 2) if temps else None,
        fuente="open-meteo",
    )


def obtener_clima(
    fecha: date | None = None, distrito: str | None = None
) -> Clima:
    """Devuelve el clima del día en un distrito, usando el caché.

    Args:
        fecha: Día consultado. Por defecto, hoy en Lima.
        distrito: Distrito del perfil. Sin él se usa Lima centro.

    Returns:
        Clima del día. Nunca lanza excepción: si todo falla recurre al
        promedio estacional, que es común a toda Lima.
    """
    fecha = fecha or datetime.now(PERU_TZ).date()
    clave = distrito if distrito in DISTRITOS else "Lima"
    cliente = service_client()

    guardado = (
        cliente.table("clima_diario")
        .select("*")
        .eq("fecha", fecha.isoformat())
        .eq("distrito", clave)
        .limit(1)
        .execute()
    )
    if guardado.data:
        fila = guardado.data[0]
        return Clima(
            humedad_media=float(fila["humedad_media"]),
            precipitacion_mm=float(fila["precipitacion_mm"]),
            temp_media=(
                float(fila["temp_media"])
                if fila["temp_media"] is not None
                else None
            ),
            fuente=fila["fuente"],
        )

    clima = _consultar_api(fecha, clave) or _estacional(fecha)

    # Solo se cachea el dato observado. El estimado no se guarda para
    # que un fallo puntual de la API no fije un valor inventado en la
    # base durante el resto del día.
    if clima.fuente == "open-meteo":
        cliente.table("clima_diario").upsert(
            {
                "fecha": fecha.isoformat(),
                "distrito": clave,
                "humedad_media": clima.humedad_media,
                "precipitacion_mm": clima.precipitacion_mm,
                "temp_media": clima.temp_media,
                "fuente": clima.fuente,
            },
            on_conflict="fecha,distrito",
        ).execute()

    return clima


@dataclass(frozen=True)
class ClimaActual:
    """Condiciones del momento, para el encabezado de Inicio.

    Attributes:
        temperatura: Grados Celsius.
        humedad: Humedad relativa en porcentaje.
        viento_kmh: Velocidad del viento en kilómetros por hora.
        observado: Momento de la medición según la fuente.
    """

    temperatura: float
    humedad: float
    viento_kmh: float
    observado: str


# Caché en memoria, por proceso. La pantalla de Inicio se abre muchas
# veces al día y el dato no cambia tanto; diez minutos evitan castigar
# a Open-Meteo sin necesidad de una tabla.
_CACHE_ACTUAL: dict[str, tuple[float, ClimaActual]] = {}
_VIGENCIA_ACTUAL = 600


def clima_actual(distrito: str | None = None) -> ClimaActual | None:
    """Devuelve las condiciones del momento en un distrito de Lima.

    Args:
        distrito: Distrito del perfil. Sin él se usa Lima centro.

    Returns:
        Condiciones actuales. Si la fuente no responde se devuelve la
        última lectura conocida de ese distrito, y None solo si nunca
        hubo ninguna.
    """
    lat, lon = coordenadas(distrito)
    clave = f"{lat},{lon}"

    ahora = time.monotonic()
    guardado = _CACHE_ACTUAL.get(clave)
    if guardado and ahora - guardado[0] < _VIGENCIA_ACTUAL:
        return guardado[1]

    parametros = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,wind_speed_10m",
        "timezone": "America/Lima",
    }
    try:
        respuesta = httpx.get(
            _API_URL, params=parametros, timeout=_TIMEOUT
        )
        respuesta.raise_for_status()
        actual = respuesta.json()["current"]
    except (httpx.HTTPError, KeyError, ValueError):
        return guardado[1] if guardado else None

    clima = ClimaActual(
        temperatura=round(float(actual["temperature_2m"]), 1),
        humedad=round(float(actual["relative_humidity_2m"])),
        viento_kmh=round(float(actual["wind_speed_10m"]), 1),
        observado=actual.get("time", ""),
    )
    _CACHE_ACTUAL[clave] = (ahora, clima)
    return clima