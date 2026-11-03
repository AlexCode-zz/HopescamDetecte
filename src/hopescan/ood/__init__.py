"""Validación de imágenes y detección fuera de dominio (OOD).

Capas, de barata a cara:

1. Validación del archivo: tamaño, formato real (PIL), resolución y limpieza
   de metadatos EXIF.
2. Heurísticas de ecografía B-mode: escala de grises, entropía, textura,
   gradiente, rango dinámico y relación de aspecto.
3. ``energy score`` sobre los logits del modelo (``logsumexp``), con umbral
   versionado en ``models/ood_calibration.json``.
4. Zona gris: confianza calibrada y margen entre las dos clases top.

La decisión final es una de:

- ``valida_confiable``: se puede mostrar la clase.
- ``valida_no_concluyente``: es una ecografía plausible, pero el modelo no
  tiene certeza suficiente; no se fuerza una clase.
- ``no_es_ecografia_mamaria``: no se muestra clase ni porcentaje.

Los umbrales por defecto son **provisionales** y están derivados de fixtures
sintéticos. No son calibración clínica. Ver ``models/ood_calibration.json``.
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, BinaryIO

import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

from ..config import (
    DEFAULT_OOD_CONFIG,
    OOD_NO_ES_ECOGRAFIA,
    OOD_VALIDA_CONFIABLE,
    OOD_VALIDA_NO_CONCLUYENTE,
)

ALLOWED_FORMATS = {"PNG", "JPEG", "WEBP", "BMP", "TIFF"}


class InvalidImageError(ValueError):
    """La imagen no se puede leer o no cumple los requisitos mínimos."""


@dataclass
class ImageFeatures:
    """Características numéricas usadas por las heurísticas."""

    width: int
    height: int
    aspect_ratio: float
    colorfulness: float
    brightness: float
    std: float
    entropy: float
    gradient: float
    unique_colors: int
    texture_ratio: float
    bright_fraction: float
    dark_fraction: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "width": self.width,
            "height": self.height,
            "aspect_ratio": round(self.aspect_ratio, 3),
            "colorfulness": round(self.colorfulness, 2),
            "brightness": round(self.brightness, 2),
            "std": round(self.std, 2),
            "entropy": round(self.entropy, 3),
            "gradient": round(self.gradient, 2),
            "unique_colors": self.unique_colors,
            "texture_ratio": round(self.texture_ratio, 3),
            "bright_fraction": round(self.bright_fraction, 3),
            "dark_fraction": round(self.dark_fraction, 3),
        }


@dataclass
class OODDecision:
    """Resultado de la validación OOD."""

    status: str
    reasons: list[str] = field(default_factory=list)
    features: dict[str, Any] = field(default_factory=dict)
    energy: float | None = None
    temperature: float = 1.0

    @property
    def is_valid(self) -> bool:
        return self.status != OOD_NO_ES_ECOGRAFIA

    @property
    def can_show_class(self) -> bool:
        return self.status == OOD_VALIDA_CONFIABLE


def _as_bytes(source: Any, max_bytes: int) -> bytes:
    """Convierte la entrada en bytes y aplica el límite de tamaño."""
    if isinstance(source, (bytes, bytearray)):
        data = bytes(source)
    elif isinstance(source, (str, Path)):
        path = Path(source)
        if not path.exists():
            raise InvalidImageError("El archivo no existe.")
        if path.stat().st_size > max_bytes:
            raise InvalidImageError(
                f"El archivo supera el límite de {max_bytes // (1024 * 1024)} MB."
            )
        data = path.read_bytes()
    elif hasattr(source, "read"):
        data = source.read()
    else:
        raise InvalidImageError("Entrada de imagen no reconocida.")

    if not data:
        raise InvalidImageError("El archivo está vacío.")
    if len(data) > max_bytes:
        raise InvalidImageError(
            f"El archivo supera el límite de {max_bytes // (1024 * 1024)} MB."
        )
    return data


def prepare_image(
    source: Image.Image | bytes | bytearray | str | Path | BinaryIO,
    *,
    config: dict[str, Any] | None = None,
) -> Image.Image:
    """Valida y normaliza una imagen para inferencia.

    - Lee el formato **real** con PIL (no confía en la extensión).
    - Rechaza archivos corruptos, vacíos, demasiado grandes o con resolución
      fuera de rango.
    - Aplica ``ImageOps.exif_transpose`` y elimina metadatos al convertir a RGB.

    Raises:
        InvalidImageError: si la imagen no es válida.
    """
    cfg = {**DEFAULT_OOD_CONFIG, **(config or {})}
    max_bytes = int(cfg.get("max_upload_mb", 15)) * 1024 * 1024
    min_side = int(cfg.get("min_side", 128))
    max_side = int(cfg.get("max_side", 8192))

    if isinstance(source, Image.Image):
        img = source.copy()
        detected_format = source.format
    else:
        data = _as_bytes(source, max_bytes)
        try:
            with Image.open(io.BytesIO(data)) as probe:
                detected_format = probe.format
                probe.verify()
            img = Image.open(io.BytesIO(data))
            img.load()
        except (UnidentifiedImageError, OSError, ValueError) as exc:
            raise InvalidImageError(
                "El archivo no es una imagen válida o está corrupto."
            ) from exc

    if detected_format and detected_format.upper() not in ALLOWED_FORMATS:
        raise InvalidImageError(
            f"Formato de imagen no admitido: {detected_format}. "
            "Usa PNG, JPG, WEBP, BMP o TIFF."
        )

    try:
        img = ImageOps.exif_transpose(img)
    except Exception:  # noqa: BLE001, S110 — EXIF corrupto no debe romper la app
        pass

    width, height = img.size
    if width < min_side or height < min_side:
        raise InvalidImageError(
            f"Resolución demasiado baja ({width}×{height}). "
            f"El mínimo es {min_side}×{min_side} píxeles."
        )
    if width > max_side or height > max_side:
        raise InvalidImageError(
            f"Resolución demasiado alta ({width}×{height}). "
            f"El máximo es {max_side}×{max_side} píxeles."
        )

    return img.convert("RGB")


def _shannon_entropy(gray: np.ndarray) -> float:
    hist = np.bincount(gray.astype(np.uint8).ravel(), minlength=256).astype(float)
    total = hist.sum()
    if total <= 0:
        return 0.0
    probabilities = hist / total
    positive = probabilities[probabilities > 0]
    return float(-(positive * np.log2(positive)).sum())


def compute_features(image: Image.Image) -> ImageFeatures:
    """Calcula las características usadas por las heurísticas B-mode."""
    rgb = np.asarray(image.convert("RGB"), dtype=np.float32)
    height, width, _ = rgb.shape

    red, green, blue = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    gray = 0.299 * red + 0.587 * green + 0.114 * blue

    colorfulness = float(
        (
            np.mean(np.abs(red - green))
            + np.mean(np.abs(green - blue))
            + np.mean(np.abs(red - blue))
        )
        / 3.0
    )
    std = float(gray.std())
    entropy = _shannon_entropy(gray)

    dx = np.abs(np.diff(gray, axis=1)) if width > 1 else np.zeros((height, 1))
    dy = np.abs(np.diff(gray, axis=0)) if height > 1 else np.zeros((1, width))
    gradient = float(dx.mean() + dy.mean())

    # Textura local: proporción de bloques 8×8 con variación apreciable.
    block = 8
    h_blocks = height // block
    w_blocks = width // block
    if h_blocks and w_blocks:
        cropped = gray[: h_blocks * block, : w_blocks * block]
        blocks = cropped.reshape(h_blocks, block, w_blocks, block).transpose(0, 2, 1, 3)
        local_std = blocks.reshape(h_blocks, w_blocks, -1).std(axis=2)
        texture_ratio = float(np.mean((local_std > 5.0) & (local_std < 45.0)))
    else:
        texture_ratio = 0.0

    bright_fraction = float(np.mean(gray > 245))
    dark_fraction = float(np.mean(gray < 10))

    return ImageFeatures(
        width=width,
        height=height,
        aspect_ratio=(width / height) if height else 0.0,
        colorfulness=colorfulness,
        brightness=float(gray.mean()),
        std=std,
        entropy=entropy,
        gradient=gradient,
        unique_colors=int(np.unique(gray.astype(np.uint8)).size),
        texture_ratio=texture_ratio,
        bright_fraction=bright_fraction,
        dark_fraction=dark_fraction,
    )


def heuristic_verdict(
    features: ImageFeatures,
    *,
    config: dict[str, Any] | None = None,
) -> tuple[str, list[str]]:
    """Aplica las heurísticas y devuelve ``(status, reasons)``.

    Los rechazos duros implican ``no_es_ecografia_mamaria``. Una sola señal
    blanda implica ``valida_no_concluyente``; dos o más también rechazan.
    """
    cfg = {**DEFAULT_OOD_CONFIG, **(config or {})}
    hard: list[str] = []
    soft: list[str] = []

    if features.width < cfg["min_side"] or features.height < cfg["min_side"]:
        hard.append("resolucion_minima")
    if not (cfg["aspect_min"] <= features.aspect_ratio <= cfg["aspect_max"]):
        hard.append("razon_aspecto_fuera_rango")
    if features.colorfulness > cfg["colorfulness_max"]:
        hard.append("imagen_en_color")
    if features.std < cfg["std_min"]:
        hard.append("imagen_plana")
    if features.unique_colors < cfg["unique_colors_min"]:
        hard.append("pocos_tonos")
    if features.std > cfg["std_max"]:
        hard.append("contraste_extremo")
    if features.entropy < cfg["entropy_min"]:
        hard.append("entropia_baja")
    if features.entropy > cfg["entropy_max"]:
        hard.append("entropia_alta_ruido")
    if features.gradient < cfg["gradient_min"]:
        hard.append("sin_textura")
    if features.gradient > cfg["gradient_max"]:
        hard.append("ruido_excesivo")

    if not (4.5 <= features.entropy <= 7.6):
        soft.append("entropia_limite")
    if not (12.0 <= features.gradient <= 75.0):
        soft.append("textura_limite")
    if features.texture_ratio < 0.05:
        soft.append("speckle_bajo")
    if features.unique_colors < 64:
        soft.append("gama_limitada")
    if features.bright_fraction > 0.60:
        soft.append("sobreexpuesta")
    if features.dark_fraction > 0.60:
        soft.append("subexpuesta")

    if hard:
        return OOD_NO_ES_ECOGRAFIA, hard + soft
    if len(soft) >= 2:
        return OOD_NO_ES_ECOGRAFIA, soft
    if len(soft) == 1:
        return OOD_VALIDA_NO_CONCLUYENTE, soft
    return OOD_VALIDA_CONFIABLE, []


def energy_score(logits: np.ndarray, temperature: float = 1.0) -> float:
    """Calcula el energy score ``-T * logsumexp(logits / T)``.

    Se devuelve con signo positivo (``T * logsumexp``) para que el umbral sea
    legible: valores altos indican sobreconfianza típica de OOD en este modelo.
    """
    logits = np.asarray(logits, dtype=np.float64).reshape(-1)
    if logits.size == 0:
        raise ValueError("logits vacíos")
    t = max(float(temperature), 1e-6)
    maximum = float(np.max(logits / t))
    logsumexp = maximum + float(np.log(np.sum(np.exp(logits / t - maximum))))
    return t * logsumexp


def combine_decision(
    heuristic_status: str,
    heuristic_reasons: list[str],
    features: ImageFeatures,
    *,
    energy: float | None = None,
    top_probability: float | None = None,
    margin: float | None = None,
    config: dict[str, Any] | None = None,
) -> OODDecision:
    """Combina heurísticas, energy score y zona gris en una decisión final."""
    cfg = {**DEFAULT_OOD_CONFIG, **(config or {})}
    reasons = list(heuristic_reasons)
    status = heuristic_status

    if status == OOD_NO_ES_ECOGRAFIA:
        return OODDecision(
            status=status,
            reasons=reasons,
            features=features.as_dict(),
            energy=energy,
            temperature=float(cfg.get("temperature", 1.0)),
        )

    if energy is not None:
        threshold = cfg.get("energy_threshold")
        if threshold is not None and energy > float(threshold):
            reasons.append("energy_score_fuera_de_rango")
            return OODDecision(
                status=OOD_NO_ES_ECOGRAFIA,
                reasons=reasons,
                features=features.as_dict(),
                energy=energy,
                temperature=float(cfg.get("temperature", 1.0)),
            )

    if top_probability is not None:
        confidence_threshold = float(cfg.get("confidence_threshold", 0.60))
        margin_threshold = float(cfg.get("margin_threshold", 0.15))
        if top_probability < confidence_threshold:
            reasons.append("confianza_calibrada_baja")
            status = OOD_VALIDA_NO_CONCLUYENTE
        if margin is not None and margin < margin_threshold:
            reasons.append("clases_compitiendo")
            status = OOD_VALIDA_NO_CONCLUYENTE

    return OODDecision(
        status=status,
        reasons=reasons,
        features=features.as_dict(),
        energy=energy,
        temperature=float(cfg.get("temperature", 1.0)),
    )


__all__ = [
    "ImageFeatures",
    "InvalidImageError",
    "OODDecision",
    "combine_decision",
    "compute_features",
    "energy_score",
    "heuristic_verdict",
    "prepare_image",
]
