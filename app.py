"""HopeScan — entrypoint Streamlit (orquesta layout + tabs).

Delegada en src/hopescan/* toda la lógica pura; app.py solo contiene UI,
estado de sesión y flujo UX idéntico al código original.
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
from hopescan.ui.styles import CHAT_CSS, STYLE_CSS


def main() -> None:
    # ----------------------------- CONFIGURACIÓN -----------------------------
    st.set_page_config(
        page_title="HopeScam tu asistente medico personal🩺🔬",
        page_icon="🩺",
        layout="wide",
    )

    # CSS global único
    st.markdown(STYLE_CSS, unsafe_allow_html=True)
    st.markdown(CHAT_CSS, unsafe_allow_html=True)

    # ------------------------------- SESIÓN ----------------------------------
    for key, default in {
        "form_submitted": False,
        "patient_data": {},
        "scan_results": None,
        "auth_search": False,
        "current_dui": None,
    }.items():
        if key not in st.session_state:
            st.session_state[key] = default

    # ----------------------------- CARGA MODELO ------------------------------
    model, device_err = load_model()

    # ------------------------------- LAYOUT ----------------------------------
    col1, col2 = st.columns([1, 1.5])

    with col1:
        render_sidebar(title="Acerca de: Información y Contactos ℹ️")

    with col2:
        st.markdown(
            """
            <div style="background-color: #2F3E46; padding: 15px; border-radius: 10px; text-align: center; margin-bottom: 20px;">
                <h2 style="color: white; margin: 0; font-size: 1.5em;">HopeScam tu asistente medico de confianza🩺🔬 - El Salvador</h2>
            </div>
            """,
            unsafe_allow_html=True,
        )

        tab_new, tab_search = st.tabs(["🆕 Nuevo Análisis", "📂 Buscar Paciente"])

        with tab_new:
            if model is None:
                model_path = resolve_model_path() or "(ruta desconocida)"
                st.warning(
                    f"⚠️ No se pudo cargar el modelo desde `{model_path}`. "
                    "Verifique que `models/modelo_cancer_mobilenet.pth` exista. "
                    "La app no podrá realizar predicciones."
                )
            else:
                view_nuevo_analisis(model, device_err)

        with tab_search:
            view_buscar_paciente()

    # ------------------------------- CHATBOT -------------------------------
    render_widget()


if __name__ == "__main__":
    main()
