"""Contenido de la pestaña 'Nuevo Análisis': formulario + imagen + resultados.

Rediseño visual aplicando buenas prácticas de Streamlit:
- Componentes nativos (containers con borde, columnas, badges, metricas)
- Sin CSS crudo ni ``use_container_width`` (deprecado)
- Material Symbols en lugar de emojis en exceso
- Umbrales de confianza para no presentar como definitivo un resultado
  poco fiable sobre una imagen que podría no ser un ultrasonido
"""

from __future__ import annotations

import base64
from io import BytesIO

import pandas as pd
import streamlit as st
from PIL import Image

from ..config import (
    CLASS_LABELS_ES,
    CLASSES,
    CONFIDENCE_UNRELIABLE_THRESHOLD,
    CONFIDENCE_WARN_THRESHOLD,
)
from ..inference import predict_image
from ..patients import save_patient_data, validate_patient_form
from ..report import create_report_content

RESULT_COLORS = {
    "Benigno": "#0E7C7B",      # teal médico
    "Maligno": "#DC2626",      # rojo de alerta
    "Normal": "#2563EB",       # azul de normal
}


def _init_tab_state() -> None:
    """Inicializa el session_state de esta pestaña en un solo lugar."""
    defaults = {
        "form_submitted": False,
        "patient_data": {},
        "scan_results": None,
        "current_dui": None,
    }
    for key, default in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default


def _render_patient_form() -> None:
    """Paso 1: registro obligatorio del paciente."""
    st.subheader("Paso 1 — Datos del paciente")

    with st.container(border=True):
        with st.form(key="patient_form", border=False):
            c1, c2 = st.columns(2, vertical_alignment="bottom")
            with c1:
                nombres = st.text_input(
                    "Nombres del paciente",
                    placeholder="Juan",
                    key="nombres_input",
                )
            with c2:
                apellidos = st.text_input(
                    "Apellidos del paciente",
                    placeholder="Pérez",
                    key="apellidos_input",
                )

            c3, c4 = st.columns(2, vertical_alignment="bottom")
            with c3:
                edad = st.number_input(
                    "Edad (años)",
                    min_value=0,
                    max_value=120,
                    value=30,
                    step=1,
                    key="edad_input",
                )
            with c4:
                genero = st.selectbox(
                    "Género",
                    ["Femenino"],
                    key="genero_input",
                )

            dui = ""
            if edad >= 18:
                dui = st.text_input(
                    "DUI (Documento Único de Identidad)",
                    placeholder="01234567-8",
                    help="Obligatorio para mayores de 18 años",
                    key="dui_input",
                )

            submit_button = st.form_submit_button(
                label="Guardar datos y continuar al análisis",
                type="primary",
                width="stretch",
            )

            if submit_button:
                err = validate_patient_form(
                    nombres=nombres, apellidos=apellidos, edad=edad, dui=dui
                )
                if err is not None:
                    st.error(err)
                else:
                    st.session_state.patient_data = {
                        "nombres": nombres,
                        "apellidos": apellidos,
                        "edad": edad,
                        "genero": genero,
                        "dui": dui if edad >= 18 else "Menor de 18",
                    }
                    st.session_state.form_submitted = True
                    st.success(
                        "Datos guardados. Ahora sube la imagen de ultrasonido."
                    )
                    st.rerun()


def _render_image_upload() -> Image.Image | None:
    """Paso 2: subida de imagen de ultrasonido."""
    st.subheader("Paso 2 — Imagen de ultrasonido")

    uploaded_file = st.file_uploader(
        "Selecciona una imagen",
        type=["png", "jpg", "jpeg"],
        accept_multiple_files=False,
        key="uploader_nuevo",
        help="Formatos aceptados: PNG, JPG, JPEG",
    )

    if uploaded_file is None:
        st.info(
            "Sube una imagen de ultrasonido de mama para iniciar el análisis."
        )
        return None

    try:
        img = Image.open(uploaded_file).convert("RGB")
    except Exception as exc:
        st.error(f"No se pudo leer la imagen: {exc}")
        return None

    st.image(
        img,
        caption="Imagen de ultrasonido cargada",
        width="stretch",
        alt="Ultrasonido de mama subido por el usuario",
    )

    # Guardar base64 para el reporte
    buffered = BytesIO()
    img.save(buffered, format="JPEG")
    image_b64 = base64.b64encode(buffered.getvalue()).decode()
    if st.session_state.scan_results is None:
        st.session_state.scan_results = {}
    st.session_state.scan_results["image_b64"] = image_b64

    return img


def _render_analysis_button() -> bool:
    """Paso 3: botón de análisis predictivo."""
    st.subheader("Paso 3 — Análisis predictivo")
    return st.button(
        "Iniciar análisis con IA",
        type="primary",
        width="stretch",
        key="btn_analizar",
    )


def _render_results(model, device, image: Image.Image) -> None:
    """Paso 4: predicción y visualización de resultados con umbrales."""
    st.subheader("Paso 4 — Resultado del análisis")

    current_image_b64 = st.session_state.scan_results.get("image_b64", "")
    st.session_state.scan_results = {"image_b64": current_image_b64}

    with st.spinner("Analizando imagen con MobileNetV2..."):
        pred_idx, probs = predict_image(model, device, image)

    if pred_idx is None:
        st.error("No se pudo obtener un resultado. Intenta con otra imagen.")
        return

    resultado = CLASSES[pred_idx]
    confianza = probs[pred_idx] * 100
    label_es = CLASS_LABELS_ES.get(resultado, resultado)

    scan_results = {
        "result": resultado,
        "confidence": f"{confianza:.2f}",
        "probabilities_percent": [p * 100 for p in probs],
        "image_b64": current_image_b64,
    }
    st.session_state.scan_results.update(scan_results)

    # Guardar en base de datos (una sola vez por paciente)
    if st.session_state.current_dui != st.session_state.patient_data["dui"]:
        save_patient_data(st.session_state.patient_data, scan_results)
        st.session_state.current_dui = st.session_state.patient_data["dui"]

    # Tarjeta principal del resultado
    color = RESULT_COLORS.get(resultado, "#6B7280")
    with st.container(border=True):
        c_result, c_metric = st.columns([2, 1], vertical_alignment="center")
        with c_result:
            st.markdown(
                f"<div style='font-size:1.1rem; color:{color}; font-weight:700;'>"
                f":material/medical_services: {label_es.upper()}</div>",
                unsafe_allow_html=True,
            )
            if resultado == "Maligno":
                st.error(
                    title="Hallazgo clasificado como MALIGNO o SOSPECHOSO",
                    body=(
                        "La IA sugiere características de alto riesgo. "
                        "**Consulta a un médico especialista de inmediato.**"
                    ),
                    icon=":material/error:",
                )
            elif resultado == "Benigno":
                st.info(
                    title="Hallazgo clasificado como BENIGNO",
                    body=(
                        "La IA sugiere un patrón de bajo riesgo. "
                        "**Siempre se recomienda la revisión profesional.**"
                    ),
                    icon=":material/check_circle:",
                )
            else:
                st.success(
                    title="Hallazgo clasificado como NORMAL / SIN HALLAZGOS",
                    body=(
                        "La IA no detectó características de riesgo. "
                        "Mantén controles preventivos y consulta al médico si aparece algún síntoma."
                    ),
                    icon=":material/healing:",
                )
        with c_metric:
            st.metric(
                label="Clase predicha",
                value=resultado.upper(),
                delta=f"{confianza:.2f}% de confianza",
                delta_color="normal" if confianza >= CONFIDENCE_WARN_THRESHOLD else "inverse",
            )

    # Advertencias de confianza (sin ocultar el resultado mostrado)
    if confianza < CONFIDENCE_UNRELIABLE_THRESHOLD and confianza > 0:
        st.error(
            title="Resultado poco fiable",
            body=(
                f"La confianza del modelo es muy baja ({confianza:.2f}%). "
                "Esta imagen podría no ser un ultrasonido válido o el modelo "
                "no tiene suficiente certeza. **No uses este resultado para decisiones clínicas.**"
            ),
            icon=":material/warning:",
        )
    elif confianza < CONFIDENCE_WARN_THRESHOLD:
        st.warning(
            title="Confianza baja",
            body=(
                f"Nivel de confianza {confianza:.2f}%. "
                "El resultado se muestra como referencia, pero se recomienda revisión médica."
            ),
            icon=":material/info:",
        )

    # Gráfico de probabilidades por clase
    st.markdown("### Probabilidad por clase")
    prob_data = {
        "Clase": [CLASS_LABELS_ES.get(c, c) for c in CLASSES],
        "Probabilidad (%)": [p * 100 for p in probs],
    }
    df_prob = pd.DataFrame(prob_data)
    st.bar_chart(df_prob, x="Clase", y="Probabilidad (%)", height=260, width="stretch")

    # Aviso médico
    st.warning(
        title="Aviso médico importante",
        body=(
            "Esta aplicación es una herramienta de apoyo informativo y educativo. "
            "**NO sustituye el diagnóstico de un profesional de la salud calificado.** "
            "La interpretación final debe ser realizada por un oncólogo o radiólogo."
        ),
        icon=":material/health_and_safety:",
    )


def _render_report_download() -> None:
    """Descarga del reporte HTML."""
    results = st.session_state.scan_results
    if not results or results.get("result") is None:
        return

    st.markdown("---")
    st.subheader("Descargar reporte")

    report_content = create_report_content(
        st.session_state.patient_data, results
    )
    st.download_button(
        label="Descargar reporte en HTML",
        data=report_content,
        file_name=f"Reporte_{st.session_state.patient_data['apellidos']}_{st.session_state.current_dui}.html",
        mime="text/html",
        width="stretch",
        type="primary",
        icon=":material/download:",
    )

    report_b64 = base64.b64encode(report_content.encode("utf-8")).decode("utf-8")
    js_code = f"""
    <script>
    function openPrintWindow() {{
        var w = window.open('about:blank', '_blank');
        w.document.write(atob('{report_b64}'));
        w.document.close();
        w.focus();
        w.print();
    }}
    </script>
    """
    st.markdown(js_code, unsafe_allow_html=True)
    if st.button(
        "Abrir reporte en ventana de impresión (PDF)",
        width="stretch",
        key="btn_imprimir",
        icon=":material/print:",
    ):
        st.markdown("<script>openPrintWindow();</script>", unsafe_allow_html=True)

    if st.button(
        "Registrar nuevo paciente",
        width="stretch",
        key="btn_nuevo",
        icon=":material/add_circle:",
    ):
        st.session_state.form_submitted = False
        st.session_state.patient_data = {}
        st.session_state.scan_results = None
        st.session_state.current_dui = None
        st.rerun()


def view_nuevo_analisis(model, device) -> None:
    """Pinta la pestaña 'Nuevo Análisis'."""
    _init_tab_state()

    # Banner del paciente actual (si ya hay datos)
    if st.session_state.patient_data:
        pd_ = st.session_state.patient_data
        st.info(
            f"Paciente actual: **{pd_['nombres']} {pd_['apellidos']}** "
            f"({pd_['edad']} años)"
        )

    if not st.session_state.form_submitted:
        _render_patient_form()
        st.info(
            "Comienza llenando el formulario de registro del paciente para habilitar el análisis."
        )
        return

    # Si ya hay resultados previos de este paciente, mostrarlos sin pedir imagen de nuevo
    if (
        st.session_state.scan_results
        and st.session_state.scan_results.get("result") is not None
    ):
        st.success("Ya tienes un resultado guardado para este paciente.")
        _render_report_download()
        return

    image = _render_image_upload()
    if image is None:
        return

    if _render_analysis_button():
        _render_results(model, device, image)

    _render_report_download()
