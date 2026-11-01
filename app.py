"""HopeScan — entrypoint Streamlit.

Orquesta layout + pestañas. Delega la lógica pura en ``src/hopescan/*``.
El modelo se carga una sola vez con ``st.cache_resource`` para no recargarlo
en cada rerun.
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

# Hacer que src/ sea importable tanto si se ejecuta app.py directamente
# (streamlit run app.py) como vía shim inferencia_cancer3.py
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from hopescan.config import resolve_model_path
from hopescan.model import load_model
from hopescan.ui.buscar_paciente import view_buscar_paciente
from hopescan.ui.chat_widget import render_widget
from hopescan.ui.nuevo_analisis import view_nuevo_analisis
from hopescan.ui.sidebar_info import render_sidebar
from hopescan.ui.styles import CHAT_CSS


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


def main() -> None:
    st.set_page_config(
        page_title="HopeScan — Detección de cáncer de mama",
        page_icon=":material/medical_services:",
        layout="wide",
    )

    # CSS mínimo (solo chat flotante). El resto del estilo viene del tema
    # nativo en .streamlit/config.toml y componentes nativos de Streamlit.
    st.markdown(CHAT_CSS, unsafe_allow_html=True)

    _init_session_state()

    # Cargar modelo (cached)
    model, device_or_err = _load_model_cached()

    if model is None:
        model_path = resolve_model_path() or "(ruta desconocida)"
        st.error(
            f"No se pudo cargar el modelo desde `{model_path}`. "
            "Verifica que `modelo_cancer_mobilenet.pth` exista. "
            "La app no podrá realizar predicciones.",
            icon=":material/error:",
        )
        if device_or_err is not None:
            st.caption(f"Detalle: {device_or_err}")

    # Sidebar (columna izquierda)
    with st.sidebar:
        render_sidebar()

    # Contenido principal
    st.markdown(
        """
        <div style="display:flex; align-items:center; gap:12px; margin-bottom:8px;">
            <span style="font-size:2rem;">:material/medical_services:</span>
            <h1 style="margin:0;">HopeScan</h1>
        </div>
        <p style="color:#6B7280; margin-top:0;">
            Asistente de apoyo a la detección de cáncer de mama por ultrasonido — El Salvador.
        </p>
        """,
        unsafe_allow_html=True,
    )

    tab_new, tab_search = st.tabs(
        [
            ":material/add_circle: Nuevo análisis",
            ":material/search: Buscar paciente",
        ]
    )

    with tab_new:
        if model is not None:
            view_nuevo_analisis(model, device_or_err)
        else:
            st.warning(
                "El modelo no está disponible. No se pueden hacer predicciones hasta que se cargue correctamente.",
                icon=":material/error:",
            )

    with tab_search:
        view_buscar_paciente()

    # Chat flotante (abarca todo el ancho inferior)
    st.markdown("---")
    render_widget()


if __name__ == "__main__":
    main()
