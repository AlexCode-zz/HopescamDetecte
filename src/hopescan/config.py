"""Configuración central de HopeScan.

Agrupa constantes, rutas (con ``pathlib``) y lectura de secretos/variables de
entorno. Es el único módulo que conoce las ubicaciones de archivos y el nombre
del producto.
"""

from __future__ import annotations

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Nombre del producto (D-003)
# ---------------------------------------------------------------------------
APP_NAME = "HopeScan"

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

CLASSES = ["Benigno", "Maligno", "Normal"]
NORM_MEAN = [0.485, 0.456, 0.406]
NORM_STD = [0.229, 0.224, 0.225]
IMAGE_SIZE = 224
NUM_CLASSES = len(CLASSES)
MOBILENET_V2_FEATURES = 1280

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
PATIENT_DB_PATH = DATA_DIR / PATIENT_DB_FILENAME        # principal (datos reales, ignorado)
PATIENT_DB_PATH_FALLBACK = Path(PATIENT_DB_FILENAME)     # raíz (compatibilidad histórica)


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


# ---------------------------------------------------------------------------
# Contraseña de búsqueda (D-004)
# ---------------------------------------------------------------------------
DEFAULT_SEARCH_PASSWORD = "SALUD123"  # valor de desarrollo original


def get_search_password() -> str:
    """Lee la contraseña de búsqueda de secrets/env con fallback de desarrollo.

    Orden de prioridad:
    1. ``st.secrets["SEARCH_PASSWORD"]`` (cuando se ejecuta bajo Streamlit).
    2. Variable de entorno ``SEARCH_PASSWORD``.
    3. Valor por defecto ``SALUD123`` (solo desarrollo).
    """
    try:
        import streamlit as st  # noqa: WPS433 (import diferido para no acoplar tests)

        if hasattr(st, "secrets") and "SEARCH_PASSWORD" in st.secrets:  # type: ignore[attr-defined]
            return str(st.secrets["SEARCH_PASSWORD"])  # type: ignore[attr-defined]
    except Exception:
        pass
    return os.environ.get("SEARCH_PASSWORD", DEFAULT_SEARCH_PASSWORD)


def is_dev_password_fallback(password: str) -> bool:
    """True si se está usando el valor por defecto de desarrollo."""
    return password == DEFAULT_SEARCH_PASSWORD
