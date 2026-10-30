"""Tests de caracterización de HopeScan (lógica pura de src/hopescan).

Capturan el comportamiento esperado tras el refactor (FASE 2): carga del modelo,
predicción sobre imagen sintética, suma de probabilidades ~1, persistencia CSV
con DUI como string, reglas de validación del formulario y respuestas del chatbot.

Se ejecutan sobre el código refactorizado y deben pasar también contra el
comportamiento documentado del original (ver tests/test_original_behavior.py
para la línea base del código original con stub de Streamlit).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest
from PIL import Image

# Asegurar import de src/ desde la raíz del proyecto
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hopescan.chatbot import responder
from hopescan.config import CLASSES
from hopescan.inference import predict_image
from hopescan.model import build_mobilenet_classifier, load_model
from hopescan.patients import (
    PATIENT_DB_COLUMNS,
    load_patient_db,
    save_patient_data,
    validate_patient_form,
)
from hopescan.report import create_report_content

_COLUMNS = PATIENT_DB_COLUMNS


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def csv_tmp(tmp_path, monkeypatch):
    """Redirige PATIENT_DB_PATH / FALLBACK a un CSV temporal."""
    target = tmp_path / "patient_records.csv"
    import hopescan.config as cfg

    monkeypatch.setattr(cfg, "PATIENT_DB_PATH", target)
    monkeypatch.setattr(cfg, "PATIENT_DB_PATH_FALLBACK", tmp_path / "fallback.csv")
    return target


# ---------------------------------------------------------------------------
# 1. Carga del modelo
# ---------------------------------------------------------------------------


def test_model_is_loaded():
    model, device = load_model()
    assert model is not None
    assert device is not None
    out_features = model.classifier[1].weight.shape[0]
    assert out_features == len(CLASSES) == 3


def test_build_mobilenet_has_3_outputs():
    model = build_mobilenet_classifier()
    assert model.classifier[1].weight.shape[0] == 3


# ---------------------------------------------------------------------------
# 2. Predicción sobre imagen sintética + probabilidades ~1
# ---------------------------------------------------------------------------


def _synthetic_image() -> Image.Image:
    return Image.new("RGB", (224, 224), color=(120, 160, 200))


def test_predict_synthetic_image_returns_valid_output():
    model, device = load_model()
    pred_idx, probs = predict_image(model, device, _synthetic_image())
    assert pred_idx is not None
    assert probs is not None
    assert 0 <= pred_idx < len(CLASSES)
    assert len(probs) == len(CLASSES)


def test_probabilities_sum_to_one():
    model, device = load_model()
    _, probs = predict_image(model, device, _synthetic_image())
    assert abs(float(sum(probs)) - 1.0) < 1e-5


def test_predict_handles_rgba_and_grayscale():
    model, device = load_model()
    rgba = Image.new("RGBA", (224, 224), color=(10, 20, 30, 255)).convert("RGB")
    gray = Image.new("L", (224, 224), color=200).convert("RGB")
    for img in (rgba, gray):
        pred_idx, probs = predict_image(model, device, img)
        assert pred_idx is not None
        assert abs(float(sum(probs)) - 1.0) < 1e-5


# ---------------------------------------------------------------------------
# 3. Persistencia CSV (DUI como string, esquema sin cambios)
# ---------------------------------------------------------------------------


def test_csv_created_with_correct_columns_when_missing(csv_tmp):
    assert not csv_tmp.exists()
    df = load_patient_db()
    assert list(df.columns) == _COLUMNS
    assert df.empty


def test_csv_read_dui_as_string(csv_tmp):
    pd.DataFrame(
        [
            {
                "Nombres": "Ana",
                "Apellidos": "Perez",
                "Edad": 17,
                "Género": "Femenino",
                "DUI": "Menor de 18",
                "Fecha_Registro": "2025-01-01 10:00:00",
                "Resultado_IA": "Benigno",
                "Confianza_IA": "90.00",
            },
            {
                "Nombres": "Luis",
                "Apellidos": "Garcia",
                "Edad": 30,
                "Género": "Femenino",
                "DUI": "01234567-8",
                "Fecha_Registro": "2025-01-02 11:00:00",
                "Resultado_IA": "Maligno",
                "Confianza_IA": "85.50",
            },
        ]
    ).to_csv(csv_tmp, index=False)
    df = load_patient_db()
    assert list(df.columns) == _COLUMNS
    assert len(df) == 2
    assert pd.api.types.is_string_dtype(df["DUI"])
    assert df.loc[df["Nombres"] == "Luis", "DUI"].iloc[0] == "01234567-8"
    assert df.loc[df["Nombres"] == "Ana", "DUI"].iloc[0] == "Menor de 18"


def test_save_and_load_roundtrip(csv_tmp):
    patient_data = {
        "nombres": "Maria",
        "apellidos": "Lopez",
        "edad": 28,
        "genero": "Femenino",
        "dui": "11223344-5",
    }
    scan_results = {
        "result": "Benigno",
        "confidence": "95.00",
        "probabilities_percent": [95.0, 3.0, 2.0],
        "image_b64": "abc123",
    }
    save_patient_data(patient_data, scan_results)
    df = load_patient_db()
    assert len(df) == 1
    row = df.iloc[0]
    assert row["Nombres"] == "Maria"
    assert row["Apellidos"] == "Lopez"
    assert row["DUI"] == "11223344-5"
    assert row["Resultado_IA"] == "Benigno"
    assert float(row["Confianza_IA"]) == 95.0


def test_csv_empty_df_when_file_corrupt(csv_tmp):
    csv_tmp.write_bytes(b"\x00\x01\x02\xff\xfe\x00\x00 corrupto")
    df = load_patient_db()
    assert list(df.columns) == _COLUMNS
    assert df.empty


# ---------------------------------------------------------------------------
# 4. Reglas de validación del formulario
# ---------------------------------------------------------------------------


def test_validation_requires_names():
    assert (
        validate_patient_form(nombres="", apellidos="Perez", edad=30, dui="11111111-1")
        is not None
    )
    assert (
        validate_patient_form(nombres="Ana", apellidos="", edad=30, dui="11111111-1")
        is not None
    )


def test_validation_requires_dui_for_adults():
    assert (
        validate_patient_form(nombres="Ana", apellidos="Perez", edad=30, dui="")
        is not None
    )
    assert (
        validate_patient_form(nombres="Ana", apellidos="Perez", edad=18, dui="")
        is not None
    )


def test_validation_allows_minor_without_dui():
    assert (
        validate_patient_form(nombres="Ana", apellidos="Perez", edad=17, dui="") is None
    )


def test_validation_allows_adult_with_dui():
    assert (
        validate_patient_form(
            nombres="Ana", apellidos="Perez", edad=30, dui="11223344-5"
        )
        is None
    )


# ---------------------------------------------------------------------------
# 5. Chatbot (motor de respuestas único)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "texto, clave",
    [
        ("hola", "hola"),
        ("qué es ecoscan", "eco"),
        ("que es ecoscan", "eco"),
        ("tengo miedo", "miedo"),
        ("síntomas", "sintomas"),
        ("que hago ahora", "hago ahora"),
        ("riesgos", "riesgos"),
        ("benigno", "benigno"),
        ("maligno", "maligno"),
        ("gracias", "gracias"),
    ],
)
def test_responder_known_intents(texto, clave):
    respuesta = responder(texto)
    assert isinstance(respuesta, str)
    assert len(respuesta) > 0
    assert respuesta != "No entendí muy bien, ¿podrías explicarlo un poco más?"


def test_responder_unknown_returns_fallback():
    respuesta = responder("asdfghjkl qwerty xyzz")
    assert respuesta == "No entendí muy bien, ¿podrías explicarlo un poco más?"


def test_create_report_content_variants():
    patient_data = {
        "nombres": "Ana",
        "apellidos": "Pérez",
        "edad": 30,
        "genero": "Femenino",
        "dui": "01234567-8",
    }
    base = {"confidence": "80.00", "probabilities_percent": [10.0, 80.0, 10.0]}
    html_n = create_report_content(patient_data, {**base, "result": "Normal"})
    assert "NORMAL" in html_n and "SIN HALLAZGOS" in html_n
    assert "data:image" not in html_n
    html_b = create_report_content(
        patient_data, {**base, "result": "Benigno", "image_b64": ""}
    )
    assert "BENIGNO" in html_b and "BAJO RIESGO" in html_b
