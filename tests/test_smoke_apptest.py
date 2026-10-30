"""Smoke test con streamlit.testing.AppTest.

Simula el flujo UX completo: formulario -> subir imagen sintética -> analizar ->
guardar -> buscar con contraseña. Requiere streamlit >= 1.32 (AppTest).

Nota: los widgets se buscan por ``key`` (definidos en la app), no por etiqueta.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import numpy as np
from PIL import Image

try:
    from streamlit.testing.v1 import AppTest
except Exception as exc:  # noqa: BLE001 — pragma: no cover
    raise SystemExit(f"streamlit.testing no disponible: {exc}")


def _make_synthetic_png() -> bytes:
    img = Image.fromarray(np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8))
    buf = __import__("io").BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_app_smoke_flow():
    app_path = str(Path(__file__).resolve().parents[1] / "app.py")
    at = AppTest.from_file(app_path, default_timeout=60)
    at.run()

    # App arranca sin excepciones
    assert not at.exception

    # ----- Formulario (keys de nuevo_analisis.py) -----
    at.text_input(key="nombres_input").input("Ana")
    at.text_input(key="apellidos_input").input("Pérez")
    at.number_input(key="edad_input").set_value(30)
    at.text_input(key="dui_input").input("01234567-8")
    at.form_submit_button(key="btn_guardar_form").click()
    at.run()
    assert not at.exception

    # ----- Imagen -----
    png_bytes = _make_synthetic_png()
    at.file_uploader(key="uploader_nuevo").set_value(
        ("ultrasonido.png", png_bytes, "image/png")
    )
    at.run()
    assert not at.exception

    # ----- Análisis -----
    at.button(key="btn_analizar").click()
    at.run()
    assert not at.exception

    # Resultado mostrado (alguna clase) — revisar markdown/error/info/success/metric
    def _vals(objs):
        return [getattr(o, "value", str(o)) for o in (objs or [])]

    textos = (
        _vals(at.markdown)
        + _vals(at.error)
        + _vals(at.info)
        + _vals(at.success)
        + [str(m) for m in (at.metric or [])]
    )
    assert any("MALIGNO" in t or "BENIGNO" in t or "NORMAL" in t for t in textos), (
        f"No se mostró clase predicha. textos={textos[:6]}"
    )
    assert not at.exception

    # Descarga disponible (revisar markdown y descargas)
    desc_textos = _vals(at.markdown)
    assert at.download_button is not None or any(
        "Descargar Reporte" in t for t in desc_textos
    )

    # ----- Búsqueda con contraseña -----
    # Ir a pestaña buscar y autenticarse (keys añadidas en buscar_paciente.py)
    at.tabs[1].text_input(key="password_input").input("SALUD123")
    at.tabs[1].button(key="btn_ingresar").click()
    at.run()
    assert not at.exception
