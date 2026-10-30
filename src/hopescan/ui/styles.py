"""CSS unificado para HopeScan (cualquier vista UI hereda ``STYLE_CSS``).

Una sola copia del CSS del código original. Se sirve a través de ``app.py``
que lo impone globalmente (``st.markdown(style_css, ...)``). Ningún otro fichero
CSS duplica contenido.
"""

from __future__ import annotations

# Variables para queries automatizados en ruff --fix no aplicables; usando strings literales.
STYLE_CSS = """
<style>
    /* Establece un color de fondo suave para toda la página */
    body { background-color: #FEECEF; /* Rosa muy claro, casi blanco */ }
    /* Aumenta el ancho máximo del contenedor principal */
    .block-container { padding-top: 2rem; padding-bottom: 0rem; padding-left: 5rem; padding-right: 5rem; }

    /* Aplica estilo a TODOS los expanders dentro de la aplicación */
    .st-expander { background-color: #FFE0E6; /* Rosa medio más visible */ border-radius: 10px; margin-bottom: 10px; padding: 5px; }

    /* Estilo para los contenidos de TODOS los expanders para que el color de fondo sea consistente */
    .st-expander div[role="region"] { background-color: #FFE0E6 !important; border-radius: 0 0 10px 10px; padding: 10px; }

    /* Estilo del formulario de paciente */
    .patient-form-container { border: 2px solid #F06292; padding: 20px; border-radius: 10px; margin-bottom: 20px; background-color: #FFF8FA; }
    /* Estilo para el encabezado de las columnas */
    div[data-testid="stVerticalBlock"] > div:first-child > div:first-child { margin-bottom: 20px; }
</style>
"""

CHAT_CSS = """
<style>
    body { background-color: #FAFAFA; }
    .chat-bubble { position: fixed; bottom: 25px; right: 25px; background-color: white; color: #333; width: 60px; height: 60px; border-radius: 50%; display: flex; justify-content: center; align-items: center; font-size: 30px; cursor: pointer; z-index: 99999; box-shadow: 0 4px 8px rgba(0,0,0,0.25); border: 2px solid #F06292; }
    .chatbox { position: fixed; bottom: 100px; right: 25px; width: 320px; background: white; border-radius: 12px; padding: 12px; box-shadow: 0 5px 12px rgba(0,0,0,0.10); z-index: 99999; }
</style>
"""
