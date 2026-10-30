"""Tests de unidad para la lógica pura de src/hopescan.

Sin dependencias de Streamlit. Cubren inference, patients, chatbot, auth y report.
"""

from __future__ import annotations

import pandas as pd
from PIL import Image

from hopescan.auth import verify_search_password
from hopescan.config import CLASSES
from hopescan.inference import predict_image
from hopescan.model import build_mobilenet_classifier, load_model
from hopescan.patients import (
    PATIENT_DB_COLUMNS,
    check_dui,
    load_patient_db,
    save_patient_data,
    search_patients,
    validate_patient_form,
)
from hopescan.report import create_report_content

# ---------------------------------------------------------------------------
# inference / model
# ---------------------------------------------------------------------------


def test_model_build_has_3_outputs():
    model = build_mobilenet_classifier()
    assert model.classifier[1].weight.shape[0] == len(CLASSES) == 3


def test_load_model_real_weights(tmp_path, monkeypatch):
    """Carga el .pth real con weights_only=True y devuelve (model, device)."""
    # Asegurar que el path real se use (modelo en raíz)
    model, device = load_model()
    assert model is not None
    assert device is not None


def test_predict_image_synthetic():
    model, device = load_model()
    img = Image.new("RGB", (224, 224), color=(100, 150, 200))
    pred_idx, probs = predict_image(model, device, img)
    assert pred_idx is not None
    assert 0 <= pred_idx < 3
    assert abs(sum(probs) - 1.0) < 1e-5


def test_predict_image_rgba_converted():
    model, device = load_model()
    rgba = Image.new("RGBA", (224, 224), color=(10, 20, 30, 255))
    pred_idx, probs = predict_image(model, device, rgba)
    assert pred_idx is not None
    assert abs(sum(probs) - 1.0) < 1e-5


# ---------------------------------------------------------------------------
# patients
# ---------------------------------------------------------------------------


def test_validate_patient_form_rules():
    assert (
        validate_patient_form(nombres="", apellidos="P", edad=30, dui="1-2") is not None
    )
    assert (
        validate_patient_form(nombres="A", apellidos="", edad=30, dui="1-2") is not None
    )
    assert (
        validate_patient_form(nombres="A", apellidos="P", edad=30, dui="") is not None
    )
    assert validate_patient_form(nombres="A", apellidos="P", edad=17, dui="") is None
    assert (
        validate_patient_form(nombres="A", apellidos="P", edad=30, dui="11223344-5")
        is None
    )


def test_check_dui_format():
    assert check_dui("01234567-8") is True
    assert check_dui("") is False
    assert check_dui("Menor de 18") is True  # histórico, no bloqueado


def test_patient_db_roundtrip_atomic(tmp_path, monkeypatch):
    from hopescan import config as cfg

    target = tmp_path / "patient_records.csv"
    monkeypatch.setattr(cfg, "PATIENT_DB_PATH", target)
    monkeypatch.setattr(cfg, "PATIENT_DB_PATH_FALLBACK", tmp_path / "fallback.csv")

    patient_data = {
        "nombres": "Ana",
        "apellidos": "Pérez",
        "edad": 30,
        "genero": "Femenino",
        "dui": "01234567-8",
    }
    scan_results = {
        "result": "Benigno",
        "confidence": "98.50",
        "probabilities_percent": [98.5, 1.0, 0.5],
        "image_b64": "abc",
    }
    save_patient_data(patient_data, scan_results)

    df = load_patient_db()
    assert list(df.columns) == PATIENT_DB_COLUMNS
    assert len(df) == 1
    assert df.iloc[0]["DUI"] == "01234567-8"
    assert df.iloc[0]["Resultado_IA"] == "Benigno"

    # Segunda escritura: añade sin corromper (atómico)
    save_patient_data(patient_data, scan_results)
    df2 = load_patient_db()
    assert len(df2) == 2


def test_load_patient_db_missing_returns_empty_with_columns(tmp_path, monkeypatch):
    from hopescan import config as cfg

    target = tmp_path / "no_existe.csv"
    monkeypatch.setattr(cfg, "PATIENT_DB_PATH", target)
    monkeypatch.setattr(cfg, "PATIENT_DB_PATH_FALLBACK", tmp_path / "no_existe2.csv")
    df = load_patient_db()
    assert list(df.columns) == PATIENT_DB_COLUMNS
    assert df.empty


def test_search_patients_filters():
    df = pd.DataFrame(
        [
            {
                "Nombres": "Ana",
                "Apellidos": "Pérez",
                "Edad": 30,
                "Género": "Femenino",
                "DUI": "01234567-8",
                "Fecha_Registro": "2025-01-01 10:00:00",
                "Resultado_IA": "Benigno",
                "Confianza_IA": "98.50",
            },
            {
                "Nombres": "Luis",
                "Apellidos": "García",
                "Edad": 40,
                "Género": "Masculino",
                "DUI": "98765432-1",
                "Fecha_Registro": "2025-01-02 11:00:00",
                "Resultado_IA": "Maligno",
                "Confianza_IA": "85.00",
            },
        ]
    )
    r = search_patients(df, "ana")
    assert len(r) == 1
    assert r.iloc[0]["Nombres"] == "Ana"
    r2 = search_patients(df, "9876")
    assert len(r2) == 1
    assert r2.iloc[0]["Apellidos"] == "García"


# ---------------------------------------------------------------------------
# auth
# ---------------------------------------------------------------------------


def test_auth_compare_digest(monkeypatch):
    monkeypatch.setenv("SEARCH_PASSWORD", "CLAVE-SECRETA")
    # reset cached: get_search_password lee env en cada llamada (no caché)
    assert verify_search_password("CLAVE-SECRETA") is True
    assert verify_search_password("mal") is False
    assert verify_search_password("") is False


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------


def test_create_report_content_shape():
    patient_data = {
        "nombres": "Ana",
        "apellidos": "Pérez",
        "edad": 30,
        "genero": "Femenino",
        "dui": "01234567-8",
    }
    scan_results = {
        "result": "Maligno",
        "confidence": "85.00",
        "probabilities_percent": [5.0, 85.0, 10.0],
        "image_b64": "dGVzdA==",
    }
    html = create_report_content(patient_data, scan_results)
    assert "MALIGNO" in html
    assert "85.00" in html
    assert "⚠️ Aviso Importante" in html
    assert "data:image/jpeg;base64,dGVzdA==" in html
    assert "NO SUSTITUYE" in html


def test_create_report_content_empty():
    assert "ERROR" in create_report_content({}, {})
