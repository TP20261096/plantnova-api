import csv
import math
import mimetypes
import os
import statistics
import sys
import time
from datetime import datetime

import requests

BASE = os.environ.get(
    "PLANTNOVA_API",
    "https://plantnova-api-318393152441.us-central1.run.app",
)
EMAIL = os.environ.get("PLANTNOVA_EMAIL")
PASSWORD = os.environ.get("PLANTNOVA_PASSWORD")
N = 30
SALIDA = "latencia_diagnose.csv"


def percentil(ordenados: list[float], p: float) -> float:
    """Percentil por rango mas cercano, el metodo que se declara en el anexo."""
    k = math.ceil(p * len(ordenados))
    return ordenados[max(1, k) - 1]


def main() -> None:
    if not EMAIL or not PASSWORD:
        sys.exit("Define PLANTNOVA_EMAIL y PLANTNOVA_PASSWORD en el entorno.")

    imagen = sys.argv[1] if len(sys.argv) > 1 else "hoja.jpg"
    if not os.path.exists(imagen):
        sys.exit(f"No existe la imagen: {imagen}")

    mime = mimetypes.guess_type(imagen)[0] or "image/jpeg"
    nombre = os.path.basename(imagen)
    peso_kb = round(os.path.getsize(imagen) / 1024, 1)

    token = requests.post(
        f"{BASE}/auth/login",
        json={"email": EMAIL, "password": PASSWORD},
        timeout=30,
    ).json()["access_token"]
    cabeceras = {"Authorization": f"Bearer {token}"}

    def diagnosticar():
        with open(imagen, "rb") as f:
            return requests.post(
                f"{BASE}/diagnose",
                headers=cabeceras,
                files={"imagen": (nombre, f, mime)},
                timeout=90,
            )

    requests.get(f"{BASE}/health", timeout=90)
    inicio = time.perf_counter()
    respuesta = diagnosticar()
    frio = time.perf_counter() - inicio
    print(f"Calentamiento (descartado): {frio:.2f} s  estado {respuesta.status_code}")

    filas = []
    for i in range(1, N + 1):
        inicio = time.perf_counter()
        respuesta = diagnosticar()
        transcurrido = time.perf_counter() - inicio
        if respuesta.status_code != 201:
            sys.exit(f"Medicion {i} fallo con {respuesta.status_code}: {respuesta.text}")
        filas.append(
            {
                "n": i,
                "marca_de_tiempo": datetime.now().isoformat(timespec="seconds"),
                "imagen": nombre,
                "peso_kb": peso_kb,
                "codigo": respuesta.status_code,
                "segundos": round(transcurrido, 3),
            }
        )
        print(f"{i:>2}/{N}  {transcurrido:.3f} s")

    with open(SALIDA, "w", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(f, fieldnames=list(filas[0]))
        escritor.writeheader()
        escritor.writerows(filas)

    t = sorted(fila["segundos"] for fila in filas)
    print(f"\nRegistro escrito en {SALIDA}")
    print(f"n              {len(t)}")
    print(f"media          {statistics.fmean(t):.3f} s")
    print(f"desviacion     {statistics.stdev(t):.3f} s")
    print(f"minimo         {t[0]:.3f} s")
    print(f"mediana        {statistics.median(t):.3f} s")
    print(f"p95            {percentil(t, 0.95):.3f} s")
    print(f"maximo         {t[-1]:.3f} s")
    print(f"arranque frio  {frio:.3f} s (fuera de la muestra)")


if __name__ == "__main__":
    main()
