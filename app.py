"""HopeScan — entrypoint Streamlit.

Orquesta el layout y las pestañas. La lógica pura vive en ``src/hopescan/*``.
El modelo se carga una sola vez con ``st.cache_resource``.
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

# Hacer que src/ sea importable tanto si se ejecuta app.py directamente
# (streamlit run app.py) como vía el shim inferencia_cancer3.py.
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from hopescan.config import (
    APP_DISCLAIMER,
    APP_NAME,
    APP_TAGLINE,
    resolve_model_path,
)
from hopescan.model import load_model
from hopescan.ui.buscar_paciente import view_buscar_paciente
from hopescan.ui.chat_widget import render_widget
from hopescan.ui.nuevo_analisis import view_nuevo_analisis
from hopescan.ui.sidebar_info import render_sidebar


@st.cache_resource(show_spinner="Cargando modelo de IA...")
def _load_model_cached():
    """Cachea el modelo MobileNetV2 entre reruns."""
    path = resolve_model_path()
    if path is None or not path.exists():
        return None, None
    return load_model()


def _init_session_state() -> None:
    """Inicializa el estado de sesión en un solo lugar."""
    defaults = {
        "form_submitted": False,
        "patient_data": {},
        "scan_results": None,
        "auth_search": False,
        "current_dui": None,
    }
    for key, default in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default


def _render_header() -> None:
    st.title(APP_NAME)
    st.caption(f"{APP_TAGLINE} · El Salvador")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.badge(
            "Validación de imagen activa",
            icon=":material/verified_user:",
            color="green",
        )
    with c2:
        st.badge(
            "Resultados orientativos",
            icon=":material/info:",
            color="blue",
        )
    with c3:
        st.badge(
            "Datos sensibles protegidos",
            icon=":material/lock:",
            color="violet",
        )


def main() -> None:
    st.set_page_config(
        page_title="HopeScan · Apoyo a la detección temprana",
        page_icon=":material/medical_services:",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    _init_session_state()

    model, device_or_error = _load_model_cached()
    device_text = str(device_or_error) if model is not None else None

    with st.sidebar:
        render_sidebar(model_ready=model is not None, device=device_text)

    _render_header()
    st.divider()

    if model is None:
        model_path = resolve_model_path() or "(ruta desconocida)"
        st.error(
            f"No se pudo cargar el modelo desde `{model_path}`. "
            "Verifica que `modelo_cancer_mobilenet.pth` exista. La pestaña de "
            "análisis quedará deshabilitada.",
            icon=":material/error:",
        )
        if isinstance(device_or_error, Exception):
            st.caption(f"Detalle: {device_or_error}")

    tab_new, tab_search, tab_chat = st.tabs(
        [
            ":material/monitor_heart: Nuevo análisis",
            ":material/search: Buscar paciente",
            ":material/forum: Asistente educativo",
        ]
    )

    with tab_new:
        if model is not None:
            view_nuevo_analisis(model, device_or_error)
        else:
            st.warning(
                "El modelo no está disponible. No se pueden realizar análisis "
                "hasta que se cargue correctamente.",
                icon=":material/error:",
            )
            st.info(
                "Coloca `modelo_cancer_mobilenet.pth` en la raíz del proyecto o "
                "en `models/`, y reinicia la aplicación.",
                icon=":material/folder:",
            )

    with tab_search:
        view_buscar_paciente()

    with tab_chat:
        render_widget()

    st.divider()
    st.caption(f"{APP_NAME} · {APP_DISCLAIMER}")


if __name__ == "__main__":
    main()
