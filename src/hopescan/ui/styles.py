"""CSS mínimo para HopeScan.

La apariencia de la página se controla principalmente mediante
``.streamlit/config.toml`` (tema nativo de Streamlit) y componentes nativos
(``st.container``, ``st.columns``, ``st.badge``, etc.), siguiendo las buenas
prácticas de Streamlit. Solo se conserva el CSS del chat flotante, que no
tiene equivalente nativo.
"""

from __future__ import annotations

CHAT_CSS = """
<style>
    .chat-bubble {
        position: fixed;
        bottom: 24px;
        right: 24px;
        width: 56px;
        height: 56px;
        border-radius: 50%;
        display: flex;
        justify-content: center;
        align-items: center;
        font-size: 28px;
        cursor: pointer;
        z-index: 99999;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        border: 2px solid #0E7C7B;
        color: #0E7C7B;
    }
    .chatbox {
        position: fixed;
        bottom: 96px;
        right: 24px;
        width: 340px;
        background: white;
        border: 1px solid #E5E7EB;
        border-radius: 12px;
        padding: 12px;
        box-shadow: 0 5px 16px rgba(0, 0, 0, 0.12);
        z-index: 99999;
        font-size: 14px;
    }
</style>
"""
