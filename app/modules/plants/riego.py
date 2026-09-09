"""Cálculo de la frecuencia de riego.

La frecuencia efectiva parte de un valor base y se corrige por dos
factores independientes:

* Clima: con humedad alta o lluvia el sustrato retiene agua más
  tiempo, así que el intervalo se alarga.
* Ubicación: la exposición al sol y al viento acelera la
  evaporación, así que el intervalo se acorta.

Los factores viven en el código y no en la base de datos porque son
parámetros del algoritmo: se pueden justificar y ajustar sin migrar
el esquema.
"""

from app.core.clima import Clima

# Días entre riegos cuando la planta no tiene especie ni diagnóstico.
RIEGO_POR_DEFECTO = 3

FACTOR_UBICACION = {
    "Terraza": 0.8,
    "Patio": 0.8,
    "Jardin": 0.8,
    "Balcon": 0.9,
    "Ventana": 1.0,
    "Interior": 1.15,
}

_HUMEDAD_ALTA = 80.0
_HUMEDAD_BAJA = 60.0


def factor_clima(clima: Clima) -> float:
    """Determina el ajuste por condiciones atmosféricas.

    Args:
        clima: Clima agregado del día.

    Returns:
        Multiplicador aplicado al intervalo base.
    """
    if clima.precipitacion_mm > 0 or clima.humedad_media >= _HUMEDAD_ALTA:
        return 1.3
    if clima.humedad_media < _HUMEDAD_BAJA:
        return 0.8
    return 1.0


def calcular_frecuencia(
    base_dias: int | None,
    ubicacion: str,
    clima: Clima,
) -> int:
    """Calcula cada cuántos días debe regarse una planta.

    Args:
        base_dias: Intervalo de referencia. Proviene del diagnóstico
            vigente o, en su defecto, de la especie registrada.
        ubicacion: Valor del enum ubicacion_planta.
        clima: Clima del día del cálculo.

    Returns:
        Días entre riegos, entre 1 y 30.
    """
    base = base_dias or RIEGO_POR_DEFECTO
    efectivo = base * factor_clima(clima) * FACTOR_UBICACION.get(
        ubicacion, 1.0
    )
    return max(1, min(30, round(efectivo)))