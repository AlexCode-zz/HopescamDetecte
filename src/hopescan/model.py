"""Carga del modelo MobileNetV2 con pesos (``torch.load(..., weights_only=True)``).

Dependencia pura (no Streamlit). Verifica D-002: ``weights_only=True`` se mantuvo;
se probó que carga el state_dict real del .pth sin alterar pesos ni arquitectura.
"""

from __future__ import annotations

import torch
import torchvision.models as models

from .config import MOBILENET_V2_FEATURES, NUM_CLASSES, resolve_model_path

# Instancia MobileNetV2 con classifier apuntado a Linear(1280, len(CLASSES))
def build_mobilenet_classifier() -> torch.nn.Module:
    """Crea un MobileNetV2 listo para inferencia con la capa final correcta."""
    model = models.mobilenet_v2(weights=None)
    model.classifier[1] = torch.nn.Linear(MOBILENET_V2_FEATURES, NUM_CLASSES)
    return model


def load_model():
    """Carga el modelo y devuelve ``(model, device)``.

    Devuelte ``(None, None)`` si no se encuentra el archivo del peso.
    """
    path = resolve_model_path()
    if path is None or not path.exists():
        return None, None

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    try:
        model = build_mobilenet_classifier()
        state_dict = torch.load(path, map_location=device, weights_only=True)  # D-002
        model.load_state_dict(state_dict)
        model.to(device).eval()
        return model, device
    except Exception as exc:
        return None, exc
