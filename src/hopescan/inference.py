"""Lógica pura de inferencia (sin dependencias de Streamlit).

Carga transforms idénticos al entrenamiento (Resize 224, Normalize ImageNet)
y realiza la predicción. ``predecir_imagen`` no haceLogging ni altera estados
de Streamlit.
"""

from __future__ import annotations

from typing import Tuple

import torch
import torchvision.transforms as T
from PIL import Image

from .config import IMAGE_SIZE, NORM_MEAN, NORM_STD

# Singleton de transformación (idempotencia con st.cache_data / gets reutilizable en tests)
_TRANSFORM = T.Compose([
    T.Resize((IMAGE_SIZE, IMAGE_SIZE)),
    T.ToTensor(),
    T.Normalize(mean=NORM_MEAN, std=NORM_STD),
])


def predict_image(model: torch.nn.Module, device: torch.device,
                   image: Image.Image) -> Tuple[int | None, list[float]]:
    """Prepara y realiza la predicción sobre ``image``.

    Args:
        model: modelo MobileNetV2 listo para inferencia.
        device: dispositivo destino.
        image: imagen (RGB/RGBA/escala de grises) -> se convierte a RGB.

    Returns:
        ``(pred_idx, probs)`` donde ``pred_idx`` es la clase ganadora (0..2) o
        ``None`` en error, y ``probs`` es una lista de floats que suma 1.
    """
    try:
        img = image.convert("RGB") if image.mode != "RGB" else image
        img_tensor = _TRANSFORM(img).unsqueeze(0).to(device)
        with torch.no_grad():
            outputs = model(img_tensor)
            probs = torch.nn.functional.softmax(outputs, dim=1)[0]
            pred_idx = int(outputs.argmax(dim=1).item())
            probs_list = probs.cpu().numpy().tolist()
        return pred_idx, probs_list
    except Exception as exc:  # NOQA: BLE001 — mimetiza el behavior original
        raise RuntimeError(f"Error durante la predicción: {exc}") from exc
