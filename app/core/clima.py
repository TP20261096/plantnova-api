"""Clima diario de Lima usado para ajustar la frecuencia de riego.

El dato se obtiene de forma perezosa: la primera consulta del día
llama a Open-Meteo y guarda el resultado en la tabla clima_diario;
el resto de peticiones de esa jornada leen el caché. Si la API
externa no responde, se usa el promedio estacional de Lima para no
bloquear el cálculo de riego.
"""

from dataclasses import dataclass
from datetime import date

import httpx

from app.core.config import settings
from app.core.supabase import service_client

_API_URL = "https://api.open-meteo.com/v1/forecast"
_TIMEOUT = 6.0

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


def _consultar_api(fecha: date) -> Clima | None:
    """Consulta Open-Meteo para la fecha indicada.

    Se piden los valores por hora y se agregan aquí, en lugar de usar
    los agregados diarios, porque los primeros están disponibles para
    todo el rango de fechas del servicio.

    Args:
        fecha: Día consultado.

    Returns:
        Clima observado, o None si la API falla o no trae datos.
    """
    parametros = {
        "latitude": settings.clima_lat,
        "longitude": settings.clima_lon,
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


def obtener_clima(fecha: date | None = None) -> Clima:
    """Devuelve el clima de la fecha, usando el caché si ya existe.

    Args:
        fecha: Día consultado. Por defecto, hoy.

    Returns:
        Clima del día. Nunca lanza excepción: si todo falla recurre al
        promedio estacional.
    """
    fecha = fecha or date.today()
    cliente = service_client()

    guardado = (
        cliente.table("clima_diario")
        .select("*")
        .eq("fecha", fecha.isoformat())
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

    clima = _consultar_api(fecha) or _estacional(fecha)

    # Solo se cachea el dato observado. El estimado no se guarda para
    # que un fallo puntual de la API no fije un valor inventado en la
    # base de datos durante el resto del día.
    if clima.fuente == "open-meteo":
        cliente.table("clima_diario").upsert(
            {
                "fecha": fecha.isoformat(),
                "humedad_media": clima.humedad_media,
                "precipitacion_mm": clima.precipitacion_mm,
                "temp_media": clima.temp_media,
                "fuente": clima.fuente,
            },
            on_conflict="fecha",
        ).execute()

    return clima