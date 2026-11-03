"""HopeScan — asistente de apoyo a la detección de cáncer de mama por ultrasonido.

Este paquete contiene la lógica pura del sistema separada de la interfaz Streamlit
(``app.py``) para facilitar testing con pytest y reutilización en el CLI.
"""

from .config import (  # noqa: F401
    APP_DISCLAIMER,
    APP_NAME,
    APP_TAGLINE,
    CLASSES,
    IMAGE_SIZE,
    MODEL_CANDIDATES,
    MODEL_FILENAME,
    NUM_CLASSES,
    OOD_NO_ES_ECOGRAFIA,
    OOD_VALIDA_CONFIABLE,
    OOD_VALIDA_NO_CONCLUYENTE,
    PATIENT_DB_COLUMNS,
    PATIENT_DB_FILENAME,
    get_search_password,
    is_search_enabled,
    load_ood_config,
    resolve_model_path,
    resolve_ood_calibration_path,
    resolve_patient_db_path,
)
