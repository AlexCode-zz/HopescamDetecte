"""Lógica pura de inferencia (sin dependencias de Streamlit).

Mantiene la API histórica ``predict_image`` y añade el pipeline completo
``analyze_image``: validación OOD → energy score → calibración → Grad-CAM.

La regla de oro: si la imagen no parece una ecografía mamaria, **no se devuelve
ninguna clase ni ningún porcentaje**.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import torch
import torchvision.transforms as T
from PIL import Image

from .config import (
    CLASSES,
    IMAGE_SIZE,
    NORM_MEAN,
    NORM_STD,
    OOD_NO_ES_ECOGRAFIA,
    OOD_VALIDA_CONFIABLE,
    OOD_VALIDA_NO_CONCLUYENTE,
    load_ood_config,
)
from .gradcam import explain_prediction
from .ood import (
    InvalidImageError,
    combine_decision,
    compute_features,
    energy_score,
    heuristic_verdict,
    prepare_image,
)

# Transformación idéntica al entrenamiento.
_TRANSFORM = T.Compose(
    [
        T.Resize((IMAGE_SIZE, IMAGE_SIZE)),
        T.ToTensor(),
        T.Normalize(mean=NORM_MEAN, std=NORM_STD),
    ]
)


def _prepare_tensor(image: Image.Image, device: torch.device) -> torch.Tensor:
    rgb = image.convert("RGB") if image.mode != "RGB" else image
    return _TRANSFORM(rgb).unsqueeze(0).to(device)


def predict_logits(
    model: torch.nn.Module, device: torch.device, image: Image.Image
) -> tuple[np.ndarray, np.ndarray]:
    """Devuelve ``(logits, probabilidades_softmax)`` para una imagen."""
    try:
        tensor = _prepare_tensor(image, device)
        with torch.no_grad():
            output = model(tensor)
            logits = output[0].detach().cpu().numpy().astype(np.float64)
        shifted = np.exp(logits - np.max(logits))
        probs = shifted / shifted.sum()
        return logits, probs
    except Exception as exc:
        raise RuntimeError(f"Error durante la predicción: {exc}") from exc


def predict_image(
    model: torch.nn.Module, device: torch.device, image: Image.Image
) -> tuple[int | None, list[float]]:
    """Predicción cruda (sin OOD) para CLI y compatibilidad.

    Returns:
        ``(pred_idx, probs)`` con ``probs`` sumando 1. Para la app usa
        ``analyze_image``, que aplica validación OOD y calibración.
    """
    _, probs = predict_logits(model, device, image)
    return int(np.argmax(probs)), probs.tolist()


def classify_ood(image: Image.Image) -> str:
    """Valida la imagen solo con heurísticas (sin cargar el modelo).

    Returns:
        ``valida_confiable``, ``valida_no_concluyente`` o
        ``no_es_ecografia_mamaria``. Una imagen ilegible se trata como no
        válida en lugar de lanzar una excepción en la UI.
    """
    try:
        prepared = prepare_image(image)
    except InvalidImageError:
        return OOD_NO_ES_ECOGRAFIA
    features = compute_features(prepared)
    status, _ = heuristic_verdict(features)
    return status


def _empty_result(
    status: str,
    message: str,
    *,
    reasons: list[str] | None = None,
    features: dict[str, Any] | None = None,
    energy: float | None = None,
    temperature: float = 1.0,
    calibration: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "status": status,
        "result": None,
        "confidence": None,
        "raw_confidence": None,
        "probabilities_percent": None,
        "margin": None,
        "energy": energy,
        "temperature": temperature,
        "reasons": reasons or [],
        "features": features or {},
        "message": message,
        "gradcam": None,
        "calibration": calibration or {},
    }


def analyze_image(
    model: torch.nn.Module,
    device: torch.device,
    image: Image.Image,
    *,
    config: dict[str, Any] | None = None,
    with_gradcam: bool = True,
) -> dict[str, Any]:
    """Pipeline completo de análisis de una ecografía.

    Returns un dict con ``status``, ``result`` (o ``None``), ``confidence``,
    ``probabilities_percent`` (o ``None``), ``message``, ``reasons``, ``energy``,
    ``features``, ``gradcam`` (PIL) y metadatos de calibración.
    """
    cfg = load_ood_config()
    if config:
        cfg.update(config)
    temperature = float(cfg.get("temperature", 1.0) or 1.0)

    # 1. Validación del archivo (tipo real, tamaño, resolución, EXIF).
    try:
        prepared = prepare_image(image, config=cfg)
    except InvalidImageError as exc:
        return _empty_result(
            OOD_NO_ES_ECOGRAFIA,
            str(exc),
            reasons=["archivo_invalido"],
            calibration=cfg,
            temperature=temperature,
        )

    # 2. Heurísticas B-mode.
    features = compute_features(prepared)
    heuristic_status, reasons = heuristic_verdict(features, config=cfg)

    if heuristic_status == OOD_NO_ES_ECOGRAFIA:
        return _empty_result(
            OOD_NO_ES_ECOGRAFIA,
            (
                "Esta imagen no parece una ecografía mamaria en escala de grises. "
                "Sube una imagen de ultrasonido de mama; no se ha generado ningún "
                "diagnóstico ni porcentaje."
            ),
            reasons=reasons,
            features=features.as_dict(),
            calibration=cfg,
            temperature=temperature,
        )

    # 3. Inferencia y energy score.
    try:
        logits, raw_probs = predict_logits(model, device, prepared)
    except RuntimeError as exc:
        return _empty_result(
            OOD_VALIDA_NO_CONCLUYENTE,
            f"No se pudo analizar la imagen: {exc}",
            reasons=reasons + ["error_inferencia"],
            features=features.as_dict(),
            calibration=cfg,
            temperature=temperature,
        )

    energy = energy_score(logits, temperature)
    scaled = logits / max(temperature, 1e-6)
    scaled = scaled - scaled.max()
    calibrated = np.exp(scaled) / np.exp(scaled).sum()
    order = np.argsort(calibrated)[::-1]
    top_probability = float(calibrated[order[0]])
    margin = float(calibrated[order[0]] - calibrated[order[1]])
    predicted_idx = int(order[0])
    predicted_class = CLASSES[predicted_idx]

    # 4. Decisión combinada.
    decision = combine_decision(
        heuristic_status,
        reasons,
        features,
        energy=energy,
        top_probability=top_probability,
        margin=margin,
        config=cfg,
    )

    if decision.status == OOD_NO_ES_ECOGRAFIA:
        return _empty_result(
            OOD_NO_ES_ECOGRAFIA,
            (
                "Esta imagen no parece una ecografía mamaria compatible con el "
                "modelo. No se muestra ninguna clase ni porcentaje. Si tienes una "
                "ecografía de mama, verifica el archivo y vuelve a intentarlo."
            ),
            reasons=decision.reasons,
            features=decision.features,
            energy=energy,
            temperature=temperature,
            calibration=cfg,
        )

    if decision.status == OOD_VALIDA_NO_CONCLUYENTE:
        return _empty_result(
            OOD_VALIDA_NO_CONCLUYENTE,
            (
                "El análisis no es concluyente: el modelo no tiene certeza "
                "suficiente o dos clases compiten. No se fuerza un resultado. "
                "Consulta a un especialista y, si es posible, repite la ecografía."
            ),
            reasons=decision.reasons,
            features=decision.features,
            energy=energy,
            temperature=temperature,
            calibration=cfg,
        )

    # 5. Resultado confiable + Grad-CAM.
    gradcam = None
    if with_gradcam:
        try:
            tensor = _prepare_tensor(prepared, device)
            gradcam, _ = explain_prediction(
                model, tensor, prepared, class_idx=predicted_idx
            )
        except Exception:  # noqa: BLE001 — Grad-CAM es explicativo, no bloquea
            gradcam = None

    return {
        "status": OOD_VALIDA_CONFIABLE,
        "result": predicted_class,
        "confidence": round(top_probability * 100, 2),
        "raw_confidence": round(float(np.max(raw_probs)) * 100, 2),
        "probabilities_percent": [round(float(p) * 100, 2) for p in calibrated],
        "margin": round(margin, 4),
        "energy": round(float(energy), 4),
        "temperature": temperature,
        "reasons": decision.reasons,
        "features": decision.features,
        "message": None,
        "gradcam": gradcam,
        "calibration": cfg,
    }


def predict_image_with_ood(
    model: torch.nn.Module,
    device: torch.device,
    image: Image.Image,
    *,
    with_gradcam: bool = False,
) -> dict[str, Any]:
    """Alias compatible de ``analyze_image`` (API anterior)."""
    return analyze_image(model, device, image, with_gradcam=with_gradcam)


__all__ = [
    "analyze_image",
    "classify_ood",
    "predict_image",
    "predict_image_with_ood",
    "predict_logits",
]
