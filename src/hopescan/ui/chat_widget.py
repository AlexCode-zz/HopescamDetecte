"""Burbuja + caja de chat única y CSS único.

Provee: render de mensajes, burbuja flotante, captura de input, motor único de respuestas.
"""

from __future__ import annotations

import streamlit as st

from ..chatbot import responder
from ..ui.styles import CHAT_CSS


def init_chat_state() -> None:
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []
    if "chatbox_open" not in st.session_state:
        st.session_state.chatbox_open = False


def render_widget() -> None:
    """Renderiza CSS + burbuja + caja de chat única (sin duplicación)."""
    st.markdown(CHAT_CSS, unsafe_allow_html=True)
    init_chat_state()

    # Captura del input — definido antes de cualquier uso (evita NameError original)
    user_input = st.chat_input("Escribe tu mensaje...")
    if user_input:
        st.session_state.chat_messages.append({"role": "user", "content": user_input})
        respuesta = responder(user_input)
        st.session_state.chat_messages.append(
            {"role": "assistant", "content": respuesta}
        )

    # Burbuja flotante única que abre/cierra la caja
    st.markdown(
        """
        <div class="chat-bubble" onclick="var box = window.parent.document.getElementById('chatbox'); 
        box.style.display = (box.style.display === 'none' ? 'block' : 'none');">💬</div>
        """,
        unsafe_allow_html=True,
    )

    # Caja del chat (oculta por defecto)
    chat_header = """
    <div id="chatbox" class="chatbox" style="display:none;">
        <h4 style="margin:0; color:#F06292;">Asistente EcoScan</h4>
        <hr style="margin:5px 0 10px 0;">
    </div>
    """
    st.markdown(chat_header, unsafe_allow_html=True)

    chat_area = st.container()
    with chat_area:
        for msg in st.session_state.chat_messages:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
