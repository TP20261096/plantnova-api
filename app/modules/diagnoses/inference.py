import io
from dataclasses import dataclass

import cv2
import numpy as np
import torch
from PIL import Image, UnidentifiedImageError
from pytorch_grad_cam import GradCAM
from pytorch_grad_cam.utils.model_targets import ClassifierOutputTarget
from torchvision import transforms

from app.modules.diagnoses.model import CLASS_NAMES, cargar_modelo

# Por debajo de este porcentaje el resultado se marca como dudoso.
# Suele indicar una foto que no es una hoja o un cultivo que el
# modelo no conoce.
UMBRAL_CONFIANZA = 60.0

_preprocess = transforms.Compose(
    [
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize(
            mean=[0.485, 0.456, 0.406],
            std=[0.229, 0.224, 0.225],
        ),
    ]
)


@dataclass(frozen=True)
class Prediccion:

    clase_raw: str
    confianza: float


@dataclass(frozen=True)
class Inferencia:

    top: list[Prediccion]
    gradcam_jpg: bytes
    original_jpg: bytes

    @property
    def principal(self) -> Prediccion:
        """Clase predicha con mayor probabilidad."""
        return self.top[0]

    @property
    def confianza_baja(self) -> bool:
        """Indica si el resultado debe presentarse con reservas."""
        return self.principal.confianza < UMBRAL_CONFIANZA


def _abrir(imagen: bytes) -> Image.Image:
    
    try:
        return Image.open(io.BytesIO(imagen)).convert("RGB")
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError("El archivo no es una imagen válida") from exc


def _a_jpeg(arreglo: np.ndarray) -> bytes:
    
    bgr = cv2.cvtColor(arreglo, cv2.COLOR_RGB2BGR)
    ok, buffer = cv2.imencode(".jpg", bgr, [cv2.IMWRITE_JPEG_QUALITY, 85])
    if not ok:
        raise ValueError("No se pudo codificar la imagen")
    return buffer.tobytes()


def _superponer(base: np.ndarray, mapa: np.ndarray) -> np.ndarray:
    
    calor = cv2.applyColorMap(
        np.uint8(255 * mapa), cv2.COLORMAP_JET
    )
    calor = cv2.cvtColor(calor, cv2.COLOR_BGR2RGB) / 255.0
    mezcla = 0.5 * calor + 0.5 * base
    return np.uint8(255 * mezcla / mezcla.max())


def analizar(imagen: bytes) -> Inferencia:

    pil = _abrir(imagen)
    tensor = _preprocess(pil).unsqueeze(0)
    base = np.array(pil.resize((224, 224))).astype(np.float32) / 255.0

    modelo = cargar_modelo()
    with torch.no_grad():
        logits = modelo(tensor)
        probabilidades = torch.softmax(logits, dim=1)[0]

    valores, indices = torch.topk(probabilidades, k=3)
    top = [
        Prediccion(
            clase_raw=CLASS_NAMES[int(i)],
            confianza=round(float(v) * 100, 2),
        )
        for v, i in zip(valores, indices)
    ]

    indice_principal = int(indices[0])
    with GradCAM(model=modelo, target_layers=[modelo.cbam]) as cam:
        mapa = cam(
            input_tensor=tensor,
            targets=[ClassifierOutputTarget(indice_principal)],
        )[0]

    return Inferencia(
        top=top,
        gradcam_jpg=_a_jpeg(_superponer(base, mapa)),
        original_jpg=_a_jpeg(np.uint8(base * 255)),
    )