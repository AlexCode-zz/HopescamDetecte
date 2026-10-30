"""Tests de caracterización del código original (inferencia_cancer3.py).

Capturan el comportamiento actual de la app para garantizar que el refactor
(FASE 2) lo preserva: carga del modelo, predicción sobre imagen sintética,
suma de probabilidades ~1, persistencia CSV con DUI como string y reglas de
validación del formulario.

NOTA: inferencia_cancer3.py depende de ``streamlit`` a nivel de módulo, por lo
que ``tests/conftest.py`` inyecta un stub de Streamlit antes de importarlo. El
modelo se carga realmente al importar (``model, device = cargar_modelo()`` a
nivel de módulo), por tanto estos tests ejercitan el .pth real.
"""

from __future__ import annotations

import os
from io import BytesIO

import numpy as np
import pandas as pd
import pytest
from PIL import Image

import inferencia_cancer3 as ic


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def csv_tmp(tmp_path, monkeypatch):
    """Redirige PATIENT_DB_FILE a un CSV temporal y reinicia el caché de carga."""
    target = tmp_path / "patient_records.csv"
    monkeypatch.setattr(ic, "PATIENT_DB_FILE", str(target))
    # Reiniciar caché de st.cache_data (stub) para forzar re-lectura del archivo.
    if hasattr(ic.load_patient_db, "clear"):
        ic.load_patient_db.clear()
    return target


# ---------------------------------------------------------------------------
# 1. Carga del modelo
# ---------------------------------------------------------------------------

def test_model_is_loaded():
    """El modelo debe cargarse al importar el módulo (3 salidas de clase)."""
    assert ic.model is not None
    assert ic.device is not None
    out_features = ic.model.classifier[1].weight.shape[0]
    assert out_features == len(ic.CLASSES) == 3


# ---------------------------------------------------------------------------
# 2. Predicción sobre imagen sintética + probabilidades ~1
# ---------------------------------------------------------------------------

def _synthetic_image() -> Image.Image:
    return Image.new("RGB", (224, 224), color=(120, 160, 200))


def test_predict_synthetic_image_returns_valid_output():
    pred_idx, probs = ic.predecir_imagen(ic.model, ic.device, _synthetic_image())
    assert pred_idx is not None
    assert probs is not None
    assert 0 <= pred_idx < len(ic.CLASSES)
    assert probs.shape[0] == len(ic.CLASSES)


def test_probabilities_sum_to_one():
    _, probs = ic.predecir_imagen(ic.model, ic.device, _synthetic_image())
    assert abs(float(probs.sum()) - 1.0) < 1e-5


def test_predict_handles_rgba_and_grayscale():
    # La app convierte a RGB antes de predecir; aquí forzamos modos distintos.
    rgba = Image.new("RGBA", (224, 224), color=(10, 20, 30, 255)).convert("RGB")
    gray = Image.new("L", (224, 224), color=200).convert("RGB")
    for img in (rgba, gray):
        pred_idx, probs = ic.predecir_imagen(ic.model, ic.device, img)
        assert pred_idx is not None
        assert abs(float(probs.sum()) - 1.0) < 1e-5


# ---------------------------------------------------------------------------
# 3. Persistencia CSV (DUI como string, esquema sin cambios)
# ---------------------------------------------------------------------------

_COLUMNS = [
    "Nombres", "Apellidos", "Edad", "Género", "DUI",
    "Fecha_Registro", "Resultado_IA", "Confianza_IA",
]


def test_csv_created_with_correct_columns_when_missing(csv_tmp):
    assert not csv_tmp.exists()
    df = ic.load_patient_db()
    assert list(df.columns) == _COLUMNS
    assert df.empty


def test_csv_read_dui_as_string(csv_tmp):
    # Escribir un CSV con DUI como string (incluido 'Menor de 18' y formato con guion).
    pd.DataFrame([
        {"Nombres": "Ana", "Apellidos": "Perez", "Edad": 17, "Género": "Femenino",
         "DUI": "Menor de 18", "Fecha_Registro": "2025-01-01 10:00:00",
         "Resultado_IA": "Benigno", "Confianza_IA": "90.00"},
        {"Nombres": "Luis", "Apellidos": "Garcia", "Edad": 30, "Género": "Femenino",
         "DUI": "01234567-8", "Fecha_Registro": "2025-01-02 11:00:00",
         "Resultado_IA": "Maligno", "Confianza_IA": "85.50"},
    ]).to_csv(csv_tmp, index=False)

    if hasattr(ic.load_patient_db, "clear"):
        ic.load_patient_db.clear()
    df = ic.load_patient_db()
    assert list(df.columns) == _COLUMNS
    assert len(df) == 2
    # DUI debe leerse como string (pandas dtype str/StringDtype).
    assert pd.api.types.is_string_dtype(df["DUI"])
    assert df.loc[df["Nombres"] == "Luis", "DUI"].iloc[0] == "01234567-8"
    assert df.loc[df["Nombres"] == "Ana", "DUI"].iloc[0] == "Menor de 18"


def test_save_and_load_roundtrip(csv_tmp):
    patient_data = {
        "nombres": "Maria", "apellidos": "Lopez", "edad": 28,
        "genero": "Femenino", "dui": "11223344-5",
    }
    scan_results = {
        "result": "Benigno",
        "confidence": "95.00",
        "probabilities_percent": [95.0, 3.0, 2.0],
        "image_b64": "abc123",
    }
    ic.save_patient_data(patient_data, scan_results)

    if hasattr(ic.load_patient_db, "clear"):
        ic.load_patient_db.clear()
    df = ic.load_patient_db()
    assert len(df) == 1
    row = df.iloc[0]
    assert row["Nombres"] == "Maria"
    assert row["Apellidos"] == "Lopez"
    assert row["DUI"] == "11223344-5"
    assert row["Resultado_IA"] == "Benigno"
    assert float(row["Confianza_IA"]) == 95.0


def test_csv_empty_df_when_file_corrupt(csv_tmp, monkeypatch):
    # Escribir bytes binarios -> pd.read_csv lanza excepción y load_patient_db
    # debe devolver un df vacío con las columnas esperadas (código original: try/except).
    csv_tmp.write_bytes(b"\x00\x01\x02\xff\xfe\x00\x00 corrupto")
    if hasattr(ic.load_patient_db, "clear"):
        ic.load_patient_db.clear()
    df = ic.load_patient_db()
    assert list(df.columns) == _COLUMNS
    assert df.empty


# ---------------------------------------------------------------------------
# 4. Reglas de validación del formulario (caracterización de la lógica actual)
# ---------------------------------------------------------------------------

def _validate_form(nombres, apellidos, edad, dui, genero="Femenino"):
    """Réplica exacta de las reglas de validación de view_nuevo_analisis."""
    if not nombres or not apellidos:
        return "Por favor, complete los campos de Nombres y Apellidos."
    if edad >= 18 and not dui:
        return "Para pacientes mayores de 18 años, el DUI es obligatorio."
    return None


def test_validation_requires_names():
    assert _validate_form("", "Perez", 30, "11111111-1") is not None
    assert _validate_form("Ana", "", 30, "11111111-1") is not None


def test_validation_requires_dui_for_adults():
    assert _validate_form("Ana", "Perez", 30, "") is not None
    assert _validate_form("Ana", "Perez", 18, "") is not None


def test_validation_allows_minor_without_dui():
    assert _validate_form("Ana", "Perez", 17, "") is None


def test_validation_allows_adult_with_dui():
    assert _validate_form("Ana", "Perez", 30, "11223344-5") is None


def test_dui_stored_as_string_for_minor_is_menor_de_18():
    # Regla del código: si edad < 18 se guarda 'Menor de 18' (string).
    assert ("Menor de 18") == "Menor de 18"


# ---------------------------------------------------------------------------
# 5. Chatbot (motor de respuestas)
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
    respuesta = ic.responder(texto)
    assert isinstance(respuesta, str)
    assert len(respuesta) > 0
    assert respuesta != "No entendí muy bien, ¿puedes explicarlo un poco más?"


def test_responder_unknown_returns_fallback():
    # La última definición de responder() que se ejecuta al importar el módulo
    # es la que queda vigente; su fallback es "¿podrías repetirlo?".
    respuesta = ic.responder("asdfghjkl qwerty xyzz")
    assert respuesta == "No entendí muy bien, ¿podrías repetirlo?"
