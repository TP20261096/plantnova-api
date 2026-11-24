from functools import lru_cache

import timm
import torch
from torch import nn

from app.core.config import settings

# Orden exacto con el que ImageFolder indexó las clases durante el
# entrenamiento. El índice que devuelve el modelo se traduce con esta
# lista, así que su orden no puede alterarse jamás.
#
# El config del entrenamiento escribe estos mismos nombres con doble guion
# bajo entre cultivo y patología ("Bell_pepper__Bell_pepper_Bacterial_spot").
# Aquí van con uno solo porque es la forma que guarda disease_catalog en
# clase_raw: copiar la lista del config rompería la búsqueda de la ficha en
# las 36 clases. El orden sí coincide posición por posición y es lo único
# que el modelo necesita.
CLASS_NAMES = [
    "Bell_pepper_Bell_pepper_Bacterial_spot",
    "Bell_pepper_Bell_pepper_Healthy",
    "Brinjal_Diseased_Brinjal_Leaf_-_Cercospora_Leaf_Spot",
    "Brinjal_Fresh_Brinjal_Leaf",
    "Cabbage_Alternaria_Leaf_Spot",
    "Cabbage_Bacterial_spot_rot",
    "Cabbage_Black_Rot",
    "Cabbage_Cabbage_aphid_colony",
    "Cabbage_Downy_Mildew",
    "Cabbage_Healthy",
    "Cabbage_club_root",
    "Cabbage_ring_spot",
    "Citrus_Citrus_Black_spot",
    "Citrus_Citrus_Healthy",
    "Citrus_Citrus_canker",
    "Citrus_Citrus_greening",
    "Corn_Corn_Common_rust",
    "Corn_Corn_Gray_leaf_spot",
    "Corn_Corn_Healthy",
    "Corn_Corn_Northern_Leaf_Blight",
    "Lettuce_Bacterial",
    "Lettuce_fungal",
    "Lettuce_healthy",
    "Potato_Potato_Early_blight",
    "Potato_Potato_Healthy",
    "Potato_Potato_Late_blight",
    "Tomato_Tomato_Bacterial_spot",
    "Tomato_Tomato_Early_blight",
    "Tomato_Tomato_Healthy",
    "Tomato_Tomato_Late_blight",
    "Tomato_Tomato_Leaf_Mold",
    "Tomato_Tomato_Mosaic_virus",
    "Tomato_Tomato_Septoria_leaf_spot",
    "Tomato_Tomato_Spider_mites",
    "Tomato_Tomato_Target_Spot",
    "Tomato_Tomato_Yellow_Leaf_Curl_Virus",
]

NUM_CLASSES = len(CLASS_NAMES)

# Cabeza de clasificación. Los índices importan: el state_dict guarda
# classifier.0 (LayerNorm) y classifier.2 (Linear), de modo que el Dropout
# tiene que ocupar la posición 1 aunque no aporte parámetros.
DROPOUT = 0.3

# Identificador de timm con el que se entrenó. El sufijo indica los pesos de
# partida del ajuste fino; la arquitectura es la misma que "convnext_small".
BACKBONE = "convnext_small.in12k_ft_in1k"


class ConvNeXtPlano(nn.Module):
    """ConvNeXt-Small sin módulo de atención.

    Sustituye a la variante con CBAM tras la comparación de arquitecturas:
    el backbone se usa como extractor con num_classes=0, de modo que
    entrega el vector de 768 características ya agrupado, y encima va la
    cabeza propia de normalización y clasificación.
    """

    def __init__(
        self,
        num_classes: int,
        pretrained: bool = False,
        dropout: float = DROPOUT,
    ) -> None:

        super().__init__()
        self.backbone = timm.create_model(
            BACKBONE,
            pretrained=pretrained,
            num_classes=0,
        )
        self.num_features = self.backbone.num_features

        self.classifier = nn.Sequential(
            nn.LayerNorm(self.num_features),
            nn.Dropout(p=dropout),
            nn.Linear(self.num_features, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:

        x = self.backbone(x)
        x = self.classifier(x)
        return x

    @property
    def capa_objetivo(self) -> nn.Module:
        """Capa que observa Grad-CAM.

        Es la última etapa convolucional del backbone, la última que
        conserva resolución espacial: después de ella el vector ya está
        agrupado y no habría mapa que dibujar.
        """
        return self.backbone.stages[-1]


@lru_cache
def cargar_modelo() -> ConvNeXtPlano:

    modelo = ConvNeXtPlano(num_classes=NUM_CLASSES, pretrained=False)
    pesos = torch.load(
        settings.model_path, map_location="cpu", weights_only=True
    )
    modelo.load_state_dict(pesos)
    modelo.eval()
    return modelo
