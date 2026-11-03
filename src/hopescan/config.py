"""Configuración central de HopeScan.

Agrupa constantes, rutas (con ``pathlib``) y lectura de secretos/variables de
entorno. Es el único módulo que conoce las ubicaciones de archivos y el nombre
del producto.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Nombre del producto (D-003)
# ---------------------------------------------------------------------------
APP_NAME = "HopeScan"
APP_TAGLINE = "Apoyo a la detección temprana de cáncer de mama por ultrasonido"
APP_DISCLAIMER = (
    "Herramienta educativa de apoyo. NO es un dispositivo médico y NO sustituye "
    "el diagnóstico de un profesional de la salud."
)

# ---------------------------------------------------------------------------
# Modelo
# ---------------------------------------------------------------------------
MODEL_FILENAME = "modelo_cancer_mobilenet.pth"
# Rutas candidatas para el modelo: primero `models/`, luego la raíz del proyecto
# (fallback conservador para no romper instalaciones existentes).
MODEL_CANDIDATES = [
    Path("models") / MODEL_FILENAME,
    Path(MODEL_FILENAME),
]

# Imagen sintética versionada para el modo demostración. Está etiquetada como
# sintética: no es una ecografía de una persona real.
DEMO_IMAGE_PATH = Path("assets") / "demo" / "ecografia_sintetica.png"

CLASSES = ["Benigno", "Maligno", "Normal"]
CLASS_LABELS_ES = {
    "Benigno": "Benigno",
    "Maligno": "Maligno o sospechoso",
    "Normal": "Normal / sin hallazgos",
}
NORM_MEAN = [0.485, 0.456, 0.406]
NORM_STD = [0.229, 0.224, 0.225]
IMAGE_SIZE = 224
NUM_CLASSES = len(CLASSES)
MOBILENET_V2_FEATURES = 1280

# ---------------------------------------------------------------------------
# Validación fuera de dominio (OOD) y calibración
# ---------------------------------------------------------------------------
# Estados finales de un análisis. La UI NUNCA debe mostrar una clase cuando el
# estado no es `valida_confiable`.
OOD_VALIDA_CONFIABLE = "valida_confiable"
OOD_VALIDA_NO_CONCLUYENTE = "valida_no_concluyente"
OOD_NO_ES_ECOGRAFIA = "no_es_ecografia_mamaria"
OOD_STATUSES = (
    OOD_VALIDA_CONFIABLE,
    OOD_VALIDA_NO_CONCLUYENTE,
    OOD_NO_ES_ECOGRAFIA,
)

OOD_CALIBRATION_FILENAME = "ood_calibration.json"
OOD_CALIBRATION_CANDIDATES = [
    Path("models") / OOD_CALIBRATION_FILENAME,
    Path(OOD_CALIBRATION_FILENAME),
]

# Valores de respaldo. Se usan solo si no existe el JSON versionado; están
# derivados de los fixtures sintéticos de tests y NO son calibración clínica.
DEFAULT_OOD_CONFIG = {
    "version": "0-uncalibrated",
    "provenance": (
        "Valores provisionales derivados de fixtures sintéticos. "
        "Recalibrar con un conjunto validado de ecografías mamarias reales."
    ),
    "temperature": 1.0,
    "energy_threshold": 1.8,
    "confidence_threshold": 0.60,
    "margin_threshold": 0.15,
    "min_side": 128,
    "max_side": 8192,
    "max_upload_mb": 15,
    "colorfulness_max": 12.0,
    "entropy_min": 3.0,
    "entropy_max": 7.8,
    "gradient_min": 5.0,
    "gradient_max": 90.0,
    "std_min": 8.0,
    "std_max": 120.0,
    "unique_colors_min": 16,
    "aspect_min": 0.4,
    "aspect_max": 2.5,
}

# ---------------------------------------------------------------------------
# Base de datos de pacientes (CSV)
# ---------------------------------------------------------------------------
PATIENT_DB_FILENAME = "patient_records.csv"
PATIENT_DB_COLUMNS = [
    "Nombres",
    "Apellidos",
    "Edad",
    "Género",
    "DUI",
    "Fecha_Registro",
    "Resultado_IA",
    "Confianza_IA",
]
DATA_DIR = Path("data")
PATIENT_DB_PATH = DATA_DIR / PATIENT_DB_FILENAME  # principal (datos reales, ignorado)
PATIENT_DB_PATH_FALLBACK = Path(PATIENT_DB_FILENAME)  # raíz (compatibilidad histórica)

# ---------------------------------------------------------------------------
# RAG / chatbot
# ---------------------------------------------------------------------------
RAG_KNOWLEDGE_DIR = Path("rag") / "knowledge"
RAG_INDEX_DIR = DATA_DIR / "rag_index"
RAG_TOP_K = 4
RAG_MIN_SCORE = 0.08


def resolve_model_path() -> Path | None:
    """Devuelve la primera ruta de modelo que exista, o ``None``."""
    for candidate in MODEL_CANDIDATES:
        if candidate.exists():
            return candidate
    return None


def resolve_patient_db_path() -> Path:
    """Devuelve la ruta del CSV de pacientes a usar.

    Prioridad: ``data/patient_records.csv`` (datos reales, ignorado por git),
    luego ``patient_records.csv`` en la raíz (compatibilidad histórica). Si no
    existe ninguna, se devuelve la ruta principal para crear un CSV vacío.
    """
    if PATIENT_DB_PATH.exists():
        return PATIENT_DB_PATH
    if PATIENT_DB_PATH_FALLBACK.exists():
        return PATIENT_DB_PATH_FALLBACK
    return PATIENT_DB_PATH


def resolve_ood_calibration_path() -> Path | None:
    """Devuelve la ruta del JSON de calibración OOD, o ``None``."""
    for candidate in OOD_CALIBRATION_CANDIDATES:
        if candidate.exists():
            return candidate
    return None


def load_ood_config() -> dict:
    """Carga la calibración OOD versionada y la fusiona con los valores base.

    Un JSON incompleto o corrupto no rompe la app: se usan los valores de
    respaldo y se conserva la procedencia para poder auditar.
    """
    config = dict(DEFAULT_OOD_CONFIG)
    path = resolve_ood_calibration_path()
    if path is None:
        return config
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            config.update(loaded)
    except (OSError, ValueError):
        config["calibration_error"] = f"No se pudo leer {path}"
    return config


# ---------------------------------------------------------------------------
# Contraseña de búsqueda (D-004)
# ---------------------------------------------------------------------------
# Ya NO existe contraseña por defecto. Si no hay SEARCH_PASSWORD configurado,
# la búsqueda queda deshabilitada con un mensaje claro.


def get_search_password() -> str | None:
    """Lee ``SEARCH_PASSWORD`` de env o de ``st.secrets``.

    Returns:
        La contraseña configurada, o ``None`` si no existe o está vacía.
        No hay valor por defecto: la búsqueda se deshabilita.
    """
    env_value = os.environ.get("SEARCH_PASSWORD", "").strip()
    if env_value:
        return env_value

    try:
        import streamlit as st  # import diferido para no acoplar tests

        secrets = getattr(st, "secrets", None)
        if secrets is not None and "SEARCH_PASSWORD" in secrets:
            secret_value = str(secrets["SEARCH_PASSWORD"]).strip()
            if secret_value:
                return secret_value
    except Exception:  # noqa: BLE001, S110 — fuera de Streamlit o secrets no disponible
        pass
    return None


def is_search_enabled() -> bool:
    """True solo si hay una contraseña de búsqueda configurada."""
    return get_search_password() is not None
