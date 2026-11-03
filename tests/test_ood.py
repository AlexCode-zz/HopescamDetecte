"""Tests del pipeline OOD y de la inferencia segura.

Contrato que se verifica:

- Una imagen que no parece una ecografía mamaria devuelve
  ``no_es_ecografia_mamaria`` y **nunca** una clase, confianza o Grad-CAM.
- Una imagen válida pero sin certeza devuelve ``valida_no_concluyente`` y
  tampoco muestra una clase.
- Solo ``valida_confiable`` devuelve clase, probabilidades y Grad-CAM.
- El modelo no se ejecuta sobre imágenes que las heurísticas rechazan.
"""

from __future__ import annotations

import math
import os

import numpy as np
import pytest
import torch
from PIL import Image

from hopescan.config import (
    CLASSES,
    OOD_NO_ES_ECOGRAFIA,
    OOD_VALIDA_CONFIABLE,
    OOD_VALIDA_NO_CONCLUYENTE,
)
from hopescan.gradcam import explain_prediction
from hopescan.inference import _TRANSFORM, analyze_image, classify_ood
from hopescan.model import load_model
from hopescan.ood import (
    InvalidImageError,
    combine_decision,
    compute_features,
    energy_score,
    prepare_image,
)

REJECT_DIR = "tests/fixtures/ood/reject"
ACCEPT_DIR = "tests/fixtures/ood/accept"
REJECT_FILES = [
    "white.png",
    "black.png",
    "gray.png",
    "noise.png",
    "chessboard.png",
    "flat_synthetic.png",
    "gradient.png",
    "small_chess.png",
    "green.png",
    "red.png",
    "rgba.png",
    "bw_photo.png",
]


@pytest.fixture(scope="module")
def model_device():
    model, device = load_model()
    assert model is not None
    return model, device


def _path(directory: str, filename: str) -> str:
    return os.path.join(directory, filename)


# ---------------------------------------------------------------------------
# Heurísticas: fixtures que deben rechazarse o aceptarse
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("filename", REJECT_FILES)
def test_reject_fixtures_are_not_ultrasound(filename):
    path = _path(REJECT_DIR, filename)
    if not os.path.exists(path):
        pytest.skip(f"Fixture {filename} no existe")
    status = classify_ood(Image.open(path))
    assert status == OOD_NO_ES_ECOGRAFIA, f"{filename} debería rechazarse"


@pytest.mark.parametrize(
    "filename",
    ["ultrasynth_1.png", "ultrasynth_2.png", "ultrasynth_3.png", "ultrasynth_4.png"],
)
def test_reliable_ultrasound_fixtures(filename):
    path = _path(ACCEPT_DIR, filename)
    if not os.path.exists(path):
        pytest.skip(f"Fixture {filename} no existe")
    assert classify_ood(Image.open(path)) == OOD_VALIDA_CONFIABLE


def test_ambiguous_ultrasound_fixture_is_no_conclusive(model_device):
    model, device = model_device
    path = _path(ACCEPT_DIR, "ultrasynth_0.png")
    if not os.path.exists(path):
        pytest.skip("Fixture ultrasynth_0.png no existe")
    # Las heurísticas lo aceptan como ecografía; la falta de certeza la decide
    # el pipeline completo con la confianza calibrada.
    assert classify_ood(Image.open(path)) == OOD_VALIDA_CONFIABLE
    result = analyze_image(model, device, Image.open(path), with_gradcam=False)
    assert result["status"] == OOD_VALIDA_NO_CONCLUYENTE
    assert result["result"] is None


def test_very_small_image_is_rejected():
    assert classify_ood(Image.new("RGB", (10, 10), color=(128, 128, 128))) == (
        OOD_NO_ES_ECOGRAFIA
    )


def test_rgba_and_grayscale_are_rejected_when_flat():
    assert classify_ood(Image.new("RGBA", (224, 224), color=(10, 20, 30, 255))) == (
        OOD_NO_ES_ECOGRAFIA
    )
    assert classify_ood(Image.new("L", (224, 224), color=128)) == OOD_NO_ES_ECOGRAFIA


def test_corrupt_bytes_are_rejected_without_exception():
    assert classify_ood(b"esto no es una imagen") == OOD_NO_ES_ECOGRAFIA


# ---------------------------------------------------------------------------
# Validación de archivo
# ---------------------------------------------------------------------------


def test_prepare_image_rejects_empty_bytes():
    with pytest.raises(InvalidImageError):
        prepare_image(b"")


def test_prepare_image_rejects_oversized_file():
    tiny = Image.new("RGB", (224, 224), color=(128, 128, 128))
    import io

    buffer = io.BytesIO()
    tiny.save(buffer, format="PNG")
    with pytest.raises(InvalidImageError):
        prepare_image(buffer.getvalue(), config={"max_upload_mb": 0})


def test_prepare_image_converts_rgba_to_rgb():
    prepared = prepare_image(Image.new("RGBA", (224, 224), color=(1, 2, 3, 255)))
    assert prepared.mode == "RGB"


def test_prepare_image_rejects_unsupported_format():
    svg = (
        b'<svg xmlns="http://www.w3.org/2000/svg"><rect width="10" height="10"/></svg>'
    )
    with pytest.raises(InvalidImageError):
        prepare_image(svg)


# ---------------------------------------------------------------------------
# Contrato de analyze_image
# ---------------------------------------------------------------------------


class _ExplodingModel(torch.nn.Module):
    def forward(self, _x):  # pragma: no cover - solo debe fallar si se llama
        raise AssertionError("El modelo no debe ejecutarse sobre una imagen inválida")


@pytest.mark.parametrize("filename", ["black.png", "gray.png", "white.png"])
def test_invalid_image_never_reaches_model(filename):
    path = _path(REJECT_DIR, filename)
    if not os.path.exists(path):
        pytest.skip(f"Fixture {filename} no existe")
    result = analyze_image(
        _ExplodingModel(), torch.device("cpu"), Image.open(path), with_gradcam=True
    )
    assert result["status"] == OOD_NO_ES_ECOGRAFIA
    assert result["result"] is None
    assert result["confidence"] is None
    assert result["probabilities_percent"] is None
    assert result["gradcam"] is None


def test_no_conclusive_result_hides_class(model_device):
    model, device = model_device
    image = Image.open(_path(ACCEPT_DIR, "ultrasynth_0.png"))
    result = analyze_image(model, device, image, with_gradcam=True)
    assert result["status"] == OOD_VALIDA_NO_CONCLUYENTE
    assert result["result"] is None
    assert result["confidence"] is None
    assert result["probabilities_percent"] is None
    assert result["gradcam"] is None


def test_reliable_result_has_class_probabilities_and_gradcam(model_device):
    model, device = model_device
    image = Image.open(_path(ACCEPT_DIR, "ultrasynth_1.png"))
    result = analyze_image(model, device, image, with_gradcam=True)
    assert result["status"] == OOD_VALIDA_CONFIABLE
    assert result["result"] in CLASSES
    assert result["confidence"] is not None and 0 < result["confidence"] <= 100
    assert result["probabilities_percent"] is not None
    assert len(result["probabilities_percent"]) == 3
    assert abs(sum(result["probabilities_percent"]) - 100.0) < 0.1
    assert result["gradcam"] is not None


def test_all_reliable_fixtures_follow_status_contract(model_device):
    model, device = model_device
    statuses = set()
    for filename in [
        "ultrasynth_1.png",
        "ultrasynth_2.png",
        "ultrasynth_3.png",
        "ultrasynth_4.png",
    ]:
        result = analyze_image(
            model, device, Image.open(_path(ACCEPT_DIR, filename)), with_gradcam=False
        )
        statuses.add(result["status"])
        if result["status"] == OOD_VALIDA_CONFIABLE:
            assert result["result"] in CLASSES
            assert result["probabilities_percent"] is not None
        else:
            assert result["result"] is None
            assert result["probabilities_percent"] is None
    assert OOD_VALIDA_CONFIABLE in statuses


# ---------------------------------------------------------------------------
# Energy score y decisión combinada
# ---------------------------------------------------------------------------


def test_energy_score_matches_logsumexp():
    assert math.isclose(energy_score([0.0, 0.0, 0.0]), math.log(3), rel_tol=1e-9)
    assert energy_score([10.0, 0.0, 0.0]) > energy_score([1.0, 0.0, 0.0])


def test_energy_score_temperature_scales_result():
    logits = np.array([2.0, 1.0, 0.0])
    assert energy_score(logits, temperature=2.0) > energy_score(logits, temperature=1.0)


def test_combine_decision_rejects_high_energy():
    features = compute_features(Image.open(_path(ACCEPT_DIR, "ultrasynth_1.png")))
    decision = combine_decision(
        OOD_VALIDA_CONFIABLE,
        [],
        features,
        energy=99.0,
        top_probability=0.99,
        margin=0.98,
    )
    assert decision.status == OOD_NO_ES_ECOGRAFIA
    assert "energy_score_fuera_de_rango" in decision.reasons


def test_combine_decision_low_confidence_is_no_conclusive():
    features = compute_features(Image.open(_path(ACCEPT_DIR, "ultrasynth_1.png")))
    decision = combine_decision(
        OOD_VALIDA_CONFIABLE,
        [],
        features,
        energy=0.5,
        top_probability=0.30,
        margin=0.10,
    )
    assert decision.status == OOD_VALIDA_NO_CONCLUYENTE
    assert "confianza_calibrada_baja" in decision.reasons


# ---------------------------------------------------------------------------
# Grad-CAM
# ---------------------------------------------------------------------------


def test_gradcam_overlay_matches_image_size(model_device):
    model, device = model_device
    image = Image.open(_path(ACCEPT_DIR, "ultrasynth_1.png")).convert("RGB")
    tensor = _TRANSFORM(image).unsqueeze(0).to(device)
    overlay, class_idx = explain_prediction(model, tensor, image)
    assert overlay.size == image.size
    assert 0 <= class_idx < len(CLASSES)
