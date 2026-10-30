"""Configuración de pytest para tests de caracterización del código original.

inferencia_cancer3.py usa ``streamlit`` a nivel de módulo (``st.set_page_config``,
``st.markdown``, inicialización de ``st.session_state``, carga del modelo al importar
y renderizado de vistas). Para poder importarlo en un entorno sin servidor de Streamlit
se inyecta un *stub* mínimo de ``streamlit`` en ``sys.modules`` ANTES de importar el
módulo bajo prueba.

El stub es lo suficientemente completo para que el módulo se importe y se puedan
ejecutar las funciones puras que queremos caracterizar (carga del modelo, predicción,
persistencia CSV, chatbot) sin lanzar excepciones de Streamlit.
"""

from __future__ import annotations

import sys
import types

# Precargar torch y torchvision ANTES de inyectar cualquier stub de streamlit,
# para evitar que inspect/getmodule falle al registrar falses de torch con
# un módulo streamlit sintético en sys.modules.
import torch  # noqa: E402  (necesario antes del stub)
from torchvision import models  # noqa: E402

from contextlib import contextmanager
from typing import Any, Dict


class _DeltaGenerator:
    """Placeholder de un elemento de Streamlit (container/expander/form/column/tab)."""

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def __getattr__(self, name: str):  # noqa: D401
        def _noop(*args, **kwargs):
            return self
        return _noop


class _SessionState(dict):
    """session_state se comporta como un dict con acceso por atributo."""

    def __getattr__(self, name: str) -> Any:
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name) from None

    def __setattr__(self, name: str, value: Any) -> None:
        self[name] = value


def _make_cached(fn):
    """Imita st.cache_data / st.cache_resource: ejecuta fn una vez y guarda el
    resultado; expone .clear() para reiniciar el caché entre tests."""
    state = {"value": None, "called": False}

    def wrapper(*args, **kwargs):
        if not state["called"]:
            state["value"] = fn(*args, **kwargs)
            state["called"] = True
        return state["value"]

    def clear():
        state["value"] = None
        state["called"] = False

    wrapper.clear = clear  # type: ignore[attr-defined]
    return wrapper


def build_streamlit_stub() -> types.ModuleType:
    st = types.ModuleType("streamlit")
    st.session_state = _SessionState()

    # No-ops que devuelven None / un placeholder
    def _noop(*args, **kwargs):
        return None

    def _placeholder(*args, **kwargs):
        return _DeltaGenerator()

    def _false(*args, **kwargs):
        return False

    def _none(*args, **kwargs):
        return None

    def _first(*args, **kwargs):
        # selectbox / radio devuelven la primera opción si se pasa posicionalmente
        if args:
            return args[0]
        return None

    st.set_page_config = _noop
    st.markdown = _noop
    st.error = _noop
    st.success = _noop
    st.warning = _noop
    st.info = _noop
    st.caption = _noop
    st.text = _noop
    st.write = _noop
    st.subheader = _noop
    st.title = _noop
    st.header = _noop
    st.metric = _noop
    st.download_button = _noop
    st.dataframe = _noop
    st.image = _noop
    st.file_uploader = _none
    st.bar_chart = _noop
    st.chat_input = _none
    st.container = _placeholder
    st.stop = _noop

    @contextmanager
    def _spinner(*args, **kwargs):
        yield

    st.spinner = _spinner

    # cache_data / cache_resource -> caché real con .clear()
    st.cache_data = _make_cached
    st.cache_resource = _make_cached

    # columnas / pestañas / expander / form -> placeholders que aceptan cualquier llamada
    def _columns(*args, **kwargs):
        spec = args[0] if args else 1
        n = len(spec) if isinstance(spec, (list, tuple)) else int(spec)
        return [_DeltaGenerator() for _ in range(n)]

    def _tabs(*args, **kwargs):
        spec = args[0] if args else []
        items = spec if isinstance(spec, (list, tuple)) else args
        return [_DeltaGenerator() for _ in items]

    def _expander(*args, **kwargs):
        return _DeltaGenerator()

    def _form(*args, **kwargs):
        return _DeltaGenerator()

    st.columns = _columns
    st.tabs = _tabs
    st.expander = _expander
    st.form = _form

    # widgets de entrada con valores por defecto razonables
    def _text_input(*args, **kwargs):
        return kwargs.get("value", "")

    def _number_input(*args, **kwargs):
        return kwargs.get("value", 0)

    def _checkbox(*args, **kwargs):
        return False

    st.text_input = _text_input
    st.number_input = _number_input
    st.checkbox = _checkbox
    st.button = _false
    st.selectbox = _first

    st.chat_message = _placeholder
    st.session_state = _SessionState()

    # Catch-all: cualquier llamada de Streamlit no explícita no rompe la importación.
    def _any(*args, **kwargs):
        return None

    st.__getattr__ = lambda name: _any  # type: ignore[attr-defined]

    return st


_STUB = build_streamlit_stub()

# Inyectar el stub ANTES de cualquier import del módulo bajo prueba.
sys.modules["streamlit"] = _STUB
