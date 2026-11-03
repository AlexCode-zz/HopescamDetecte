"""Smoke test con ``streamlit.testing.AppTest``.

Recorre el flujo completo: formulario + consentimiento → ecografía válida →
análisis OOD → resultado confiable → reporte → búsqueda autenticada.

La base de pacientes se redirige a ``tmp_path`` para no tocar datos reales.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from streamlit.testing.v1 import AppTest

FIXTURE = (
    Path(__file__).resolve().parent / "fixtures" / "ood" / "accept" / "ultrasynth_1.png"
)


def _texts(at: AppTest) -> list[str]:
    values: list[str] = []
    for collection in (
        at.markdown,
        at.caption,
        at.error,
        at.info,
        at.success,
        at.warning,
    ):
        values.extend(getattr(item, "value", str(item)) for item in (collection or []))
    values.extend(str(metric) for metric in (at.metric or []))
    return values


def test_app_smoke_flow(monkeypatch, tmp_path):
    app_path = str(Path(__file__).resolve().parents[1] / "app.py")

    monkeypatch.setenv("SEARCH_PASSWORD", "clave-smoke")
    import hopescan.config as cfg

    monkeypatch.setattr(cfg, "PATIENT_DB_PATH", tmp_path / "patient_records.csv")
    monkeypatch.setattr(cfg, "PATIENT_DB_PATH_FALLBACK", tmp_path / "fallback.csv")

    at = AppTest.from_file(app_path, default_timeout=90)
    at.run()
    assert not at.exception

    # Streamlit promueve ``st.secrets`` a ``os.environ``, así que el secreto
    # local (si existe) tiene prioridad sobre la variable del test. Usamos la
    # contraseña efectiva para probar el flujo real de autenticación.
    active_password = cfg.get_search_password()
    assert active_password, "La prueba necesita una contraseña activa"

    # ----- Formulario + consentimiento -----
    at.text_input(key="nombres_input").input("Ana")
    at.text_input(key="apellidos_input").input("Pérez")
    at.number_input(key="edad_input").set_value(30)
    at.text_input(key="dui_input").input("01234567-8")
    at.checkbox(key="consent_input").check()
    at.form_submit_button(key="btn_guardar_form").click()
    at.run()
    assert not at.exception
    assert at.session_state["form_submitted"] is True

    # ----- Imagen válida -----
    assert FIXTURE.exists()
    at.file_uploader(key="uploader_nuevo").set_value(
        ("ecografia.png", FIXTURE.read_bytes(), "image/png")
    )
    at.run()
    assert not at.exception

    # ----- Análisis -----
    at.button(key="btn_analizar").click()
    at.run()
    assert not at.exception
    result = at.session_state["scan_results"]
    assert result is not None
    assert result["status"] == "valida_confiable"
    assert result["result"] in {"Benigno", "Maligno", "Normal"}
    assert result["confidence"] is not None
    assert result["gradcam"] is not None

    texts = _texts(at)
    assert any("Normal" in text or "NORMAL" in text for text in texts), texts[:10]
    assert at.download_button, "Debe ofrecerse el reporte HTML"

    # ----- Búsqueda con contraseña -----
    # ``AppTest`` no conserva el valor de widgets dentro de ``st.form`` entre
    # reruns; se inyecta en session_state y se pulsa el botón para ejercitar
    # el flujo real de autenticación.
    at.session_state["password_input"] = active_password
    at.tabs[1].button(key="btn_ingresar").click()
    at.run()
    assert not at.exception
    assert at.session_state["auth_search"] is True
