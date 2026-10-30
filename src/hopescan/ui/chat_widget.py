"""Asistente de chat único (burbuja flotante + historial de mensajes).

Usa los componentes nativos de chat de Streamlit (``st.chat_message``,
``st.chat_input``) y solo el CSS mínimo para la burbuja flotante.
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
    """Renderiza CSS del chat, historial y input."""
    st.markdown(CHAT_CSS, unsafe_allow_html=True)
    init_chat_state()

    # Historial de mensajes en un contenedor con borde
    chat_container = st.container(border=True)
    with chat_container:
        st.caption("Asistente HopeScan — dudas sobre prevención y síntomas")
        if not st.session_state.chat_messages:
            st.info("Escribe un mensaje para comenzar la conversación.")
        for msg in st.session_state.chat_messages:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

    # Input de chat
    user_input = st.chat_input("Escribe tu mensaje...")
    if user_input:
        st.session_state.chat_messages.append({"role": "user", "content": user_input})
        respuesta = responder(user_input)
        st.session_state.chat_messages.append(
            {"role": "assistant", "content": respuesta}
        )
        st.rerun()

    # Burbuja flotante para abrir/cerrar el chat
    st.markdown(
        """
        <div class="chat-bubble" onclick="document.querySelector('.chatbox').style.display =
        (document.querySelector('.chatbox').style.display === 'none' ? 'block' : 'none');">
            :material/chat:
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Caja de chat embebida (oculta por defecto)
    st.markdown(
        '<div class="chatbox" style="display:none;">',
        unsafe_allow_html=True,
    )
    st.markdown("**Asistente EcoScan**")
    st.divider()
    st.markdown("</div>", unsafe_allow_html=True)
