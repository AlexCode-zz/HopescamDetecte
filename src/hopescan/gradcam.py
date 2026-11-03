"""Grad-CAM para explicar la predicción sobre la imagen.

Implementación mínima y sin dependencias extra: hooks sobre la última capa
convolucional de MobileNetV2, mapa de activación normalizado y superposición
con una rampa de color tipo ``jet``.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import torch
from PIL import Image


class GradCAM:
    """Genera mapas de activación Grad-CAM para un modelo de clasificación."""

    def __init__(
        self, model: torch.nn.Module, target_layer: torch.nn.Module | None = None
    ):
        self.model = model
        self.target_layer = target_layer or model.features[-1]
        self.activations: torch.Tensor | None = None
        self.gradients: torch.Tensor | None = None
        self._handles = [
            self.target_layer.register_forward_hook(self._forward_hook),
            self.target_layer.register_full_backward_hook(self._backward_hook),
        ]

    def _forward_hook(self, _module: Any, _inputs: Any, output: torch.Tensor) -> None:
        self.activations = output

    def _backward_hook(
        self, _module: Any, _grad_inputs: Any, grad_outputs: Any
    ) -> None:
        self.gradients = grad_outputs[0]

    def generate(
        self, input_tensor: torch.Tensor, class_idx: int | None = None
    ) -> tuple[np.ndarray, int]:
        """Devuelve ``(heatmap, class_idx)`` con el mapa en rango [0, 1]."""
        self.model.zero_grad(set_to_none=True)
        tensor = input_tensor.detach().clone().requires_grad_(True)

        with torch.enable_grad():
            logits = self.model(tensor)
            if class_idx is None:
                class_idx = int(logits.argmax(dim=1).item())
            score = logits[0, class_idx]
            score.backward()

        if self.activations is None or self.gradients is None:
            raise RuntimeError(
                "No se capturaron activaciones/gradientes para Grad-CAM."
            )

        activations = self.activations.detach()[0]
        gradients = self.gradients.detach()[0]
        weights = gradients.mean(dim=(1, 2))
        cam = torch.relu((weights[:, None, None] * activations).sum(dim=0))
        cam = cam - cam.min()
        maximum = cam.max()
        if float(maximum) > 0:
            cam = cam / maximum
        return cam.cpu().numpy(), int(class_idx)

    def close(self) -> None:
        for handle in self._handles:
            handle.remove()
        self._handles.clear()

    def __enter__(self) -> GradCAM:  # noqa: PYI034 — Self requiere Python 3.11
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()


def _jet_colormap(cam: np.ndarray) -> np.ndarray:
    """Rampa de color tipo jet, implementada con numpy (sin matplotlib)."""
    cam = np.clip(np.asarray(cam, dtype=np.float32), 0.0, 1.0)
    stops = np.array(
        [
            [0.0, 0.0, 0.0, 128.0],
            [0.25, 0.0, 128.0, 255.0],
            [0.5, 0.0, 255.0, 128.0],
            [0.75, 255.0, 255.0, 0.0],
            [1.0, 255.0, 0.0, 0.0],
        ],
        dtype=np.float32,
    )
    positions = stops[:, 0]
    channels = stops[:, 1:]
    output = np.zeros((*cam.shape, 3), dtype=np.float32)
    for channel in range(3):
        output[..., channel] = np.interp(cam, positions, channels[:, channel])
    return output.astype(np.uint8)


def overlay_heatmap(
    image: Image.Image, cam: np.ndarray, *, alpha: float = 0.45
) -> Image.Image:
    """Superpone el mapa Grad-CAM sobre la imagen original."""
    base = image.convert("RGB")
    heat = Image.fromarray(_jet_colormap(cam)).resize(
        base.size, Image.Resampling.BILINEAR
    )
    blended = Image.blend(base, heat, alpha=alpha)
    return blended


def explain_prediction(
    model: torch.nn.Module,
    input_tensor: torch.Tensor,
    image: Image.Image,
    *,
    class_idx: int | None = None,
    alpha: float = 0.45,
) -> tuple[Image.Image, int]:
    """Atajo: genera Grad-CAM y devuelve ``(imagen_superpuesta, class_idx)``."""
    with GradCAM(model) as gradcam:
        heatmap, predicted = gradcam.generate(input_tensor, class_idx=class_idx)
    return overlay_heatmap(image, heatmap, alpha=alpha), predicted


__all__ = ["GradCAM", "explain_prediction", "overlay_heatmap"]
