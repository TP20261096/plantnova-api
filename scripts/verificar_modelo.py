import sys

import torch

from app.core.config import settings
from app.modules.diagnoses.inference import analizar
from app.modules.diagnoses.model import CLASS_NAMES, NUM_CLASSES, cargar_modelo


def main() -> None:
    imagen = sys.argv[1] if len(sys.argv) > 1 else "hoja.jpg"

    print(f"Archivo de pesos: {settings.model_path}")

    modelo = cargar_modelo()
    print(f"Clase del modelo: {type(modelo).__name__}")
    print(f"Caracteristicas:  {modelo.num_features}")
    print(f"Clases:           {NUM_CLASSES}")
    print(f"Capa objetivo:    {type(modelo.capa_objetivo).__name__}")

    parametros = sum(p.numel() for p in modelo.parameters())
    print(f"Parametros:       {parametros:,}  (el config declara 49,483,908)")

    with torch.no_grad():
        salida = modelo(torch.zeros(1, 3, 224, 224))
    print(f"Forma de salida:  {tuple(salida.shape)}  (se espera (1, {NUM_CLASSES}))")

    with open(imagen, "rb") as f:
        resultado = analizar(f.read())

    print("\nTop 3:")
    for p in resultado.top:
        print(f"  {p.confianza:6.2f} %  {p.clase_raw}")

    assert resultado.top[0].clase_raw in CLASS_NAMES

    with open("verificacion_original.jpg", "wb") as f:
        f.write(resultado.original_jpg)
    with open("verificacion_gradcam.jpg", "wb") as f:
        f.write(resultado.gradcam_jpg)


if __name__ == "__main__":
    main()
