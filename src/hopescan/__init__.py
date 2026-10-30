"""HopeScan — asistente de apoyo a la detección de cáncer de mama por ultrasonido.

Este paquete contiene la lógica pura del sistema separada de la interfaz Streamlit
(``app.py``) para facilitar testing con pytest y reutilización en el CLI.
"""

from .config import (  # noqa: E402, F401
    APP_NAME,
    CLASSES,
    IMAGE_SIZE,
    NUM_CLASSES,
    MODEL_CANDIDATES,
    MODEL_FILENAME,
    resolve_model_path,
    resolve_patient_db_path,
    get_search_password,
    is_dev_password_fallback,
    DEFAULT_SEARCH_PASSWORD,
    PATIENT_DB_COLUMNS,
    PATIENT_DB_FILENAME,
)
