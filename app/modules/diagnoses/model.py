from functools import lru_cache

import timm
import torch
from torch import nn

from app.core.config import settings

# Orden exacto con el que ImageFolder indexó las clases durante el
# entrenamiento. El índice que devuelve el modelo se traduce con esta
# lista, así que su orden no puede alterarse jamás.
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


class CBAM(nn.Module):

    def __init__(self, channels: int, reduction: int = 16) -> None:
        
        super().__init__()
        self.avg_pool = nn.AdaptiveAvgPool2d(1)
        self.max_pool = nn.AdaptiveMaxPool2d(1)
        self.fc = nn.Sequential(
            nn.Conv2d(channels, channels // reduction, 1, bias=False),
            nn.ReLU(),
            nn.Conv2d(channels // reduction, channels, 1, bias=False),
        )
        self.sigmoid = nn.Sigmoid()
        self.conv_spa = nn.Conv2d(
            2, 1, kernel_size=7, padding=3, bias=False
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        
        avg_out = self.fc(self.avg_pool(x))
        max_out = self.fc(self.max_pool(x))
        x = x * self.sigmoid(avg_out + max_out)

        avg_s = torch.mean(x, dim=1, keepdim=True)
        max_s, _ = torch.max(x, dim=1, keepdim=True)
        x = x * self.sigmoid(
            self.conv_spa(torch.cat([avg_s, max_s], dim=1))
        )
        return x


class ConvNeXtWithCBAM(nn.Module):
    
    def __init__(
        self,
        num_classes: int,
        pretrained: bool = False,
        dropout: float = 0.3,
    ) -> None:
        
        super().__init__()
        self.backbone = timm.create_model(
            "convnext_tiny",
            pretrained=pretrained,
            num_classes=0,
            global_pool="",
        )
        self.num_features = self.backbone.num_features

        self.cbam = CBAM(self.num_features, reduction=16)
        self.pool = nn.AdaptiveAvgPool2d(1)

        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.LayerNorm(self.num_features),
            nn.Dropout(p=dropout),
            nn.Linear(self.num_features, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        
        x = self.backbone(x)
        x = self.cbam(x)
        x = self.pool(x)
        x = self.classifier(x)
        return x


@lru_cache
def cargar_modelo() -> ConvNeXtWithCBAM:
    
    modelo = ConvNeXtWithCBAM(
        num_classes=NUM_CLASSES, pretrained=False
    )
    pesos = torch.load(
        settings.model_path, map_location="cpu", weights_only=True
    )
    modelo.load_state_dict(pesos)
    modelo.eval()
    return modelo