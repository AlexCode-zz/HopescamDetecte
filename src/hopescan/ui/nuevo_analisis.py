"""Pestaña «Nuevo análisis»: paciente, imagen y resultado seguro.

La regla central es simple: **si la imagen no es una ecografía mamaria válida o
el modelo no tiene certeza suficiente, no se muestra ninguna clase ni ningún
porcentaje**. La UI solo presenta la clase, las probabilidades y el Grad-CAM
cuando el estado es ``valida_confiable``.

Se usan componentes nativos de Streamlit (contenedores, columnas, badges,
métricas, gráficos) y el tema de ``.streamlit/config.toml``. No se inyecta CSS
ni JavaScript.
"""

from __future__ import annotations

import base64
import re
import uuid
from io import BytesIO
from pathlib import Path

import pandas as pd
import streamlit as st
from PIL import Image

from ..config import (
    CLASS_LABELS_ES,
    CLASSES,
    DEMO_IMAGE_PATH,
    OOD_NO_ES_ECOGRAFIA,
    OOD_VALIDA_CONFIABLE,
    OOD_VALIDA_NO_CONCLUYENTE,
    load_ood_config,
)
from ..inference import analyze_image
from ..ood import InvalidImageError, compute_features, prepare_image
from ..patients import mask_dui, save_patient_data, validate_patient_form
from ..report import create_report_content

_REASON_LABELS = {
    "resolucion_minima": "La resolución es demasiado baja para una ecografía.",
    "razon_aspecto_fuera_rango": "La proporción de la imagen no es compatible con una ecografía.",
    "imagen_en_color": "La imagen contiene color; una ecografía B-mode suele ser en escala de grises.",
    "imagen_plana": "La imagen es casi uniforme, sin textura de tejido.",
    "pocos_tonos": "La imagen tiene muy pocos tonos de gris.",
    "contraste_extremo": "El contraste es extremo para una ecografía.",
    "entropia_baja": "La distribución de tonos es demasiado simple.",
    "entropia_alta_ruido": "La imagen parece ruido, no tejido.",
    "sin_textura": "No se detecta textura de tejido.",
    "ruido_excesivo": "Hay demasiado ruido o bordes artificiales.",
    "entropia_limite": "La textura está en el límite de lo esperado.",
    "textura_limite": "La textura está en el límite de lo esperado.",
    "speckle_bajo": "No se observa el moteado típico del ultrasonido.",
    "gama_limitada": "La gama de grises es limitada.",
    "sobreexpuesta": "La imagen está sobreexpuesta.",
    "subexpuesta": "La imagen está subexpuesta.",
    "confianza_calibrada_baja": "La confianza calibrada del modelo es baja.",
    "clases_compitiendo": "Dos clases tienen probabilidades muy parecidas.",
    "energy_score_fuera_de_rango": "El modelo detectó un patrón atípico (energy score alto).",
    "archivo_invalido": "El archivo no se pudo leer como una imagen válida.",
    "error_inferencia": "Ocurrió un error durante la inferencia.",
}

_CLASS_STYLES = {
    "Maligno": {
        "badge": "Hallazgo sospechoso",
        "color": "red",
        "icon": ":material/priority_high:",
        "title": "Hallazgo sospechoso",
        "body": (
            "El modelo encontró un patrón compatible con malignidad. "
            "**Esto no es un diagnóstico.** Acude a un profesional de la salud "
            "para una valoración prioritaria."
        ),
    },
    "Benigno": {
        "badge": "Patrón de bajo riesgo",
        "color": "blue",
        "icon": ":material/check_circle:",
        "title": "Patrón de bajo riesgo",
        "body": (
            "El modelo encontró un patrón compatible con benignidad. "
            "**Esto no descarta una enfermedad.** Lleva el resultado a una "
            "revisión profesional."
        ),
    },
    "Normal": {
        "badge": "Sin hallazgos evidentes",
        "color": "green",
        "icon": ":material/healing:",
        "title": "Sin hallazgos evidentes",
        "body": (
            "El modelo no detectó patrones de riesgo relevantes. "
            "**Esto no es una garantía de salud.** Mantén los controles "
            "preventivos y consulta ante cualquier cambio."
        ),
    },
}


def _init_tab_state() -> None:
    """Inicializa el estado de esta pestaña sin pisar valores existentes."""
    defaults = {
        "form_submitted": False,
        "patient_data": {},
        "scan_results": None,
        "current_dui": None,
        "consent_granted": False,
        "demo_mode": False,
        "demo_image_bytes": None,
        "demo_defaults_applied": False,
        "analysis_id": None,
        "saved_analysis_id": None,
        "current_image_b64": "",
        "save_error": None,
    }
    for key, default in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default


def _render_progress(step: int) -> None:
    labels = {1: "Paciente", 2: "Imagen", 3: "Resultado"}
    st.progress(step / 3, text=f"Paso {step} de 3 · {labels[step]}")


# ---------------------------------------------------------------------------
# Paso 1: paciente
# ---------------------------------------------------------------------------


def _apply_demo_defaults(enabled: bool) -> None:
    """Rellena o limpia los campos con datos ficticios al cambiar el modo."""
    applied = bool(st.session_state.get("demo_defaults_applied"))
    if enabled and not applied:
        st.session_state.nombres_input = "Paciente"
        st.session_state.apellidos_input = "Demostración"
        st.session_state.edad_input = 42
        st.session_state.genero_input = "Femenino"
        st.session_state.dui_input = "01234567-8"
        st.session_state.demo_defaults_applied = True
    elif not enabled and applied:
        st.session_state.nombres_input = ""
        st.session_state.apellidos_input = ""
        st.session_state.edad_input = 30
        st.session_state.genero_input = "Femenino"
        st.session_state.dui_input = ""
        st.session_state.demo_defaults_applied = False


def _reset_patient_fields() -> None:
    for key in (
        "nombres_input",
        "apellidos_input",
        "edad_input",
        "genero_input",
        "dui_input",
        "consent_input",
    ):
        st.session_state.pop(key, None)
    st.session_state.demo_defaults_applied = False


def _render_patient_form() -> None:
    """Paso 1: datos mínimos, consentimiento y modo demostración."""
    st.subheader("Paso 1 · Datos del paciente")
    st.caption(
        "Los datos se guardan en un CSV local. En modo demostración se usan "
        "datos ficticios y no se escribe ningún registro."
    )

    demo_mode = st.toggle(
        "Modo demostración",
        key="demo_mode",
        help=(
            "Rellena el formulario con un paciente ficticio y evita guardar el "
            "resultado en la base local. Útil para probar la app sin datos reales."
        ),
    )
    _apply_demo_defaults(bool(demo_mode))
    if demo_mode:
        st.info(
            "Modo demostración activo: los datos son ficticios y el resultado "
            "no se guardará.",
            icon=":material/science:",
        )

    with st.container(border=True), st.form(key="patient_form", border=False):
        st.markdown("#### Identificación")
        c1, c2 = st.columns(2)
        with c1:
            nombres = st.text_input(
                "Nombres *",
                placeholder="Ana",
                key="nombres_input",
            )
        with c2:
            apellidos = st.text_input(
                "Apellidos *",
                placeholder="Pérez",
                key="apellidos_input",
            )

        c3, c4 = st.columns(2)
        with c3:
            edad = st.number_input(
                "Edad (años) *",
                min_value=0,
                max_value=120,
                value=30,
                step=1,
                key="edad_input",
            )
        with c4:
            genero = st.selectbox(
                "Género",
                ["Femenino", "Masculino", "Otro", "Prefiero no decir"],
                key="genero_input",
            )

        dui = st.text_input(
            "DUI",
            placeholder="01234567-8",
            help=(
                "Obligatorio para mayores de 18 años. No registres el DUI de "
                "una persona menor de edad."
            ),
            key="dui_input",
        )

        consent = st.checkbox(
            "Confirmo que tengo autorización para analizar esta imagen y que "
            "entiendo que HopeScan no emite un diagnóstico.",
            key="consent_input",
        )

        submitted = st.form_submit_button(
            "Guardar y continuar",
            type="primary",
            width="stretch",
            icon=":material/arrow_forward:",
            key="btn_guardar_form",
        )

        if submitted:
            error = validate_patient_form(
                nombres=nombres,
                apellidos=apellidos,
                edad=int(edad),
                dui=dui,
            )
            if error is not None:
                st.error(error, icon=":material/error:")
            elif not consent:
                st.error(
                    "Debes confirmar que tienes autorización para analizar la "
                    "imagen antes de continuar.",
                    icon=":material/error:",
                )
            else:
                st.session_state.patient_data = {
                    "nombres": nombres.strip(),
                    "apellidos": apellidos.strip(),
                    "edad": int(edad),
                    "genero": genero,
                    "dui": dui.strip() if edad >= 18 else "Menor de 18",
                }
                st.session_state.consent_granted = True
                st.session_state.form_submitted = True
                st.session_state.scan_results = None
                st.session_state.analysis_id = None
                st.session_state.saved_analysis_id = None
                st.rerun()


# ---------------------------------------------------------------------------
# Paso 2: imagen
# ---------------------------------------------------------------------------


def _clear_image() -> None:
    """Callback: elimina la imagen cargada o de demostración."""
    st.session_state.demo_image_bytes = None
    st.session_state.pop("uploader_nuevo", None)


def _load_demo_image() -> None:
    """Callback: carga la ecografía sintética versionada."""
    try:
        st.session_state.demo_image_bytes = Path(DEMO_IMAGE_PATH).read_bytes()
        st.session_state.pop("uploader_nuevo", None)
    except OSError:
        st.session_state.demo_image_bytes = None


def _image_to_b64(image: Image.Image, fmt: str = "JPEG") -> str:
    buffer = BytesIO()
    image.save(buffer, format=fmt, quality=90)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def _render_patient_summary() -> None:
    """Tarjeta compacta con el paciente de la sesión."""
    patient = st.session_state.patient_data or {}
    if not patient:
        return

    def _edit_patient() -> None:
        st.session_state.form_submitted = False
        st.session_state.patient_data = {}
        st.session_state.consent_granted = False
        st.session_state.scan_results = None
        st.session_state.analysis_id = None
        st.session_state.saved_analysis_id = None
        st.session_state.demo_image_bytes = None
        st.session_state.save_error = None
        st.session_state.pop("uploader_nuevo", None)
        st.session_state.pop("consent_input", None)

    with st.container(border=True):
        c1, c2 = st.columns([3, 1], vertical_alignment="center")
        with c1:
            st.markdown(
                f"**{patient.get('nombres', '')} {patient.get('apellidos', '')}**"
            )
            st.caption(
                f"{patient.get('edad', '—')} años · {patient.get('genero', '—')} · "
                f"DUI: {mask_dui(patient.get('dui', '')) or 'No registrado'}"
            )
            if st.session_state.demo_mode:
                st.badge(
                    "Paciente ficticio de demostración",
                    icon=":material/science:",
                    color="violet",
                )
        with c2:
            st.button(
                "Editar datos",
                icon=":material/edit:",
                width="stretch",
                key="btn_editar_paciente",
                on_click=_edit_patient,
            )


def _render_image_upload() -> tuple[Image.Image, bytes] | None:
    """Paso 2: subida, validación básica y vista previa."""
    st.subheader("Paso 2 · Imagen de ecografía")
    st.caption(
        "Sube una ecografía mamaria en escala de grises. Formatos: PNG, JPG, "
        "WEBP, BMP o TIFF (máximo 15 MB)."
    )

    uploaded_file = st.file_uploader(
        "Selecciona la imagen",
        type=["png", "jpg", "jpeg", "webp", "bmp", "tif", "tiff"],
        accept_multiple_files=False,
        key="uploader_nuevo",
        help=(
            "Evita capturas de pantalla, imágenes en color y fotos de baja "
            "resolución. La imagen se procesa en memoria."
        ),
        max_upload_size=15,
    )

    demo_bytes = st.session_state.get("demo_image_bytes")
    source_bytes: bytes | None = None
    source_label = ""
    if uploaded_file is not None:
        source_bytes = uploaded_file.getvalue()
        source_label = "Archivo cargado"
    elif demo_bytes:
        source_bytes = bytes(demo_bytes)
        source_label = "Ecografía sintética de demostración"

    c1, c2 = st.columns([1, 1])
    with c1:
        st.button(
            "Usar imagen de demostración",
            icon=":material/science:",
            width="stretch",
            key="btn_demo_image",
            on_click=_load_demo_image,
        )
    with c2:
        st.button(
            "Quitar imagen",
            icon=":material/delete:",
            width="stretch",
            key="btn_clear_image",
            on_click=_clear_image,
            disabled=source_bytes is None,
        )

    if source_bytes is None:
        st.info(
            "Sube una imagen para continuar. Si no tienes una a mano, usa la "
            "ecografía sintética de demostración.",
            icon=":material/upload:",
        )
        return None

    try:
        prepared = prepare_image(source_bytes, config=load_ood_config())
    except InvalidImageError as exc:
        st.error(
            title="No se pudo leer la imagen",
            body=str(exc),
            icon=":material/error:",
        )
        return None

    features = compute_features(prepared)
    image_b64 = _image_to_b64(prepared)
    st.session_state.current_image_b64 = image_b64

    left, right = st.columns([1.2, 1], vertical_alignment="top")
    with left:
        st.image(
            prepared,
            caption=source_label,
            width="stretch",
            alt="Ecografía mamaria cargada para el análisis",
        )
    with right, st.container(border=True):
        st.markdown("#### Archivo validado")
        st.caption(
            f"{features.width}×{features.height} px · {len(source_bytes) / 1024:.0f} KB"
        )
        if features.colorfulness <= load_ood_config().get("colorfulness_max", 12.0):
            st.badge("Escala de grises", icon=":material/contrast:", color="gray")
        else:
            st.badge(
                "Imagen en color",
                icon=":material/palette:",
                color="orange",
            )
        st.caption(
            "La comprobación definitiva de que sea una ecografía mamaria se "
            "ejecuta al analizar. Si no lo es, no se mostrará ninguna clase."
        )

    return prepared, source_bytes


def _run_analysis(
    model,
    device,
    image: Image.Image,
    image_bytes: bytes,
) -> None:
    """Ejecuta el pipeline completo y deja el resultado en la sesión."""
    with st.status("Analizando imagen...", expanded=True) as status:
        st.write("Comprobando que la imagen sea una ecografía mamaria...")
        result = analyze_image(model, device, image, with_gradcam=True)

        if result["status"] == OOD_NO_ES_ECOGRAFIA:
            status.update(
                label="La imagen no parece una ecografía mamaria",
                state="error",
                expanded=False,
            )
        elif result["status"] == OOD_VALIDA_NO_CONCLUYENTE:
            status.update(
                label="Análisis completado: no concluyente",
                state="complete",
                expanded=False,
            )
        else:
            status.update(
                label="Análisis completado",
                state="complete",
                expanded=False,
            )

    result["image_b64"] = _image_to_b64(image)
    if result.get("gradcam") is not None:
        result["gradcam_b64"] = _image_to_b64(result["gradcam"])
    result["image_bytes"] = len(image_bytes)
    result["analysis_id"] = uuid.uuid4().hex
    st.session_state.scan_results = result
    st.session_state.analysis_id = result["analysis_id"]
    st.session_state.saved_analysis_id = None
    st.session_state.save_error = None

    # Guardar una sola vez, nunca en modo demostración ni para imágenes inválidas.
    if (
        not st.session_state.demo_mode
        and result["status"] != OOD_NO_ES_ECOGRAFIA
        and st.session_state.patient_data
    ):
        record = dict(result)
        record["result"] = result.get("result") or "No concluyente"
        record["confidence"] = (
            result.get("confidence") if result.get("confidence") is not None else "N/A"
        )
        try:
            save_patient_data(st.session_state.patient_data, record)
            st.session_state.saved_analysis_id = result["analysis_id"]
            st.session_state.current_dui = st.session_state.patient_data.get("dui")
        except Exception as exc:  # noqa: BLE001 — no debe romper el resultado
            st.session_state.save_error = str(exc)

    st.rerun()


# ---------------------------------------------------------------------------
# Paso 3: resultados
# ---------------------------------------------------------------------------


def _render_reasons(reasons: list[str]) -> None:
    if not reasons:
        return
    seen: list[str] = []
    for reason in reasons:
        text = _REASON_LABELS.get(reason, reason.replace("_", " ").capitalize())
        if text not in seen:
            seen.append(text)
    with st.expander("¿Por qué se tomó esta decisión?", expanded=False):
        for text in seen:
            st.markdown(f"- {text}")


def _render_technical(result: dict) -> None:
    calibration = result.get("calibration") or {}
    with st.expander("Detalles técnicos del análisis", expanded=False):
        c1, c2 = st.columns(2)
        energy = result.get("energy")
        c1.metric(
            "Energy score",
            f"{energy:.3f}" if energy is not None else "No calculado",
            help=(
                "Puntuación de energía del modelo. Valores altos sugieren que la "
                "imagen se aleja de las ecografías usadas en entrenamiento."
            ),
        )
        c2.metric(
            "Temperatura de calibración",
            f"{float(result.get('temperature', 1.0)):.2f}",
        )
        st.caption(
            f"Estado: `{result.get('status', 'desconocido')}` · "
            f"Calibración: `{calibration.get('version', 'desconocida')}` "
            f"({calibration.get('calibration_status', 'sin estado')})"
        )
        st.caption(
            "Los umbrales son provisionales y provienen de fixtures sintéticos; "
            "no son calibración clínica."
        )
        features = result.get("features") or {}
        if features:
            st.dataframe(
                pd.DataFrame(
                    [
                        {"Métrica": key, "Valor": value}
                        for key, value in features.items()
                    ]
                ),
                hide_index=True,
                width="stretch",
                height=260,
            )


def _render_probabilities(result: dict) -> None:
    probabilities = result.get("probabilities_percent") or []
    if not probabilities:
        return
    st.markdown("#### Distribución de probabilidades")
    frame = pd.DataFrame(
        {
            "Clase": [CLASS_LABELS_ES.get(name, name) for name in CLASSES],
            "Probabilidad (%)": [float(value) for value in probabilities],
        }
    )
    st.bar_chart(
        frame,
        x="Clase",
        y="Probabilidad (%)",
        horizontal=True,
        height=260,
        color="#DB2777",
    )
    st.caption(
        "La confianza es una medida técnica del modelo, no una probabilidad de "
        "tener o no cáncer."
    )


def _render_gradcam(result: dict) -> None:
    gradcam = result.get("gradcam")
    if gradcam is None:
        return
    st.markdown("#### Explicación visual (Grad-CAM)")
    st.caption(
        "El mapa de calor muestra dónde se fijó el modelo. Las zonas cálidas no "
        "señalan una lesión ni un diagnóstico."
    )
    c1, c2 = st.columns(2)
    with c1:
        st.image(
            Image.open(BytesIO(base64.b64decode(result["image_b64"]))),
            caption="Imagen analizada",
            width="stretch",
            alt="Ecografía original analizada",
        )
    with c2:
        st.image(
            gradcam,
            caption="Grad-CAM sobre la imagen",
            width="stretch",
            alt="Mapa de calor Grad-CAM sobre la ecografía",
        )


def _render_confident(result: dict) -> None:
    result_class = result.get("result")
    style = _CLASS_STYLES.get(
        result_class,
        {
            "badge": "Resultado",
            "color": "blue",
            "icon": ":material/info:",
            "title": "Resultado",
            "body": "El modelo emitió una clase, pero no es un diagnóstico.",
        },
    )
    confidence = float(result.get("confidence") or 0.0)
    margin = result.get("margin")
    label = CLASS_LABELS_ES.get(result_class, result_class or "—")

    with st.container(border=True):
        st.badge(style["badge"], icon=style["icon"], color=style["color"])
        if result_class == "Maligno":
            st.error(
                title=style["title"],
                body=style["body"],
                icon=":material/priority_high:",
            )
        elif result_class == "Benigno":
            st.info(
                title=style["title"],
                body=style["body"],
                icon=":material/check_circle:",
            )
        else:
            st.success(
                title=style["title"],
                body=style["body"],
                icon=":material/healing:",
            )

        c1, c2 = st.columns(2)
        c1.metric(
            "Confianza calibrada",
            f"{confidence:.1f}%",
            help="Confianza del modelo después de la calibración por temperatura.",
        )
        c2.metric(
            "Margen entre clases",
            f"{float(margin) * 100:.1f} pp" if margin is not None else "—",
            help="Diferencia entre la clase más probable y la segunda.",
        )
        st.caption(
            f"Clase mostrada: **{label}**. La confianza no es una probabilidad de "
            "cáncer y el resultado debe revisarlo un profesional."
        )

    _render_probabilities(result)
    _render_gradcam(result)
    _render_reasons(result.get("reasons") or [])
    _render_technical(result)
    st.warning(
        title="Aviso médico importante",
        body=(
            "HopeScan es una herramienta educativa de apoyo. **NO sustituye el "
            "diagnóstico de un profesional de la salud.** La interpretación final "
            "debe realizarla un oncólogo o radiólogo."
        ),
        icon=":material/health_and_safety:",
    )


def _render_no_conclusive(result: dict) -> None:
    with st.container(border=True):
        st.badge(
            "Análisis no concluyente",
            icon=":material/help:",
            color="orange",
        )
        st.warning(
            title="El modelo no tiene certeza suficiente",
            body=result.get("message")
            or (
                "No se fuerza un resultado. Esto no significa que exista una "
                "enfermedad; significa que el modelo no alcanzó el umbral de "
                "confianza."
            ),
            icon=":material/warning:",
        )
        st.info(
            "No se muestra una clase ni un porcentaje porque hacerlo sería "
            "engañoso. Consulta a un especialista y, si es posible, repite la "
            "ecografía.",
            icon=":material/info:",
        )
    _render_reasons(result.get("reasons") or [])
    _render_technical(result)
    st.warning(
        title="Aviso médico importante",
        body=(
            "Un resultado no concluyente no descarta ni confirma ninguna "
            "enfermedad. La valoración de un profesional es indispensable."
        ),
        icon=":material/health_and_safety:",
    )


def _render_invalid(result: dict) -> None:
    with st.container(border=True):
        st.badge(
            "Imagen no válida",
            icon=":material/block:",
            color="red",
        )
        st.error(
            title="La imagen no parece una ecografía mamaria",
            body=result.get("message")
            or (
                "No se generó ninguna clase ni ningún porcentaje. Sube una "
                "ecografía de mama en escala de grises."
            ),
            icon=":material/error:",
        )
        st.info(
            "No se emitió ningún resultado clínico. Esto evita presentar como "
            "«normal» una imagen que el modelo no debería analizar.",
            icon=":material/info:",
        )
        st.markdown(
            "**Qué revisar:**\n"
            "- Que sea una ecografía y no una foto, un dibujo o una captura de pantalla.\n"
            "- Que esté en escala de grises y tenga textura de tejido.\n"
            "- Que la resolución sea suficiente y la imagen no esté en blanco o negro."
        )
    _render_reasons(result.get("reasons") or [])
    _render_technical(result)


def _render_report_download(result: dict) -> None:
    if result.get("status") == OOD_NO_ES_ECOGRAFIA:
        return
    patient = st.session_state.patient_data or {}
    report = create_report_content(patient, result)
    surname = re.sub(
        r"[^A-Za-z0-9_-]+", "_", str(patient.get("apellidos", "paciente"))
    ).strip("_")
    st.download_button(
        "Descargar reporte en HTML",
        data=report,
        file_name=f"Reporte_HopeScan_{surname or 'paciente'}.html",
        mime="text/html",
        width="stretch",
        type="primary",
        icon=":material/download:",
    )
    st.caption(
        "El reporte incluye el estado del análisis, la confianza, las "
        "probabilidades y el Grad-CAM cuando corresponde. Ábrelo y usa "
        "Imprimir → Guardar como PDF."
    )


def _clear_analysis() -> None:
    st.session_state.scan_results = None
    st.session_state.analysis_id = None
    st.session_state.saved_analysis_id = None
    st.session_state.current_image_b64 = ""
    st.session_state.demo_image_bytes = None
    st.session_state.save_error = None
    st.session_state.pop("uploader_nuevo", None)


def _reset_all() -> None:
    st.session_state.form_submitted = False
    st.session_state.patient_data = {}
    st.session_state.scan_results = None
    st.session_state.current_dui = None
    st.session_state.consent_granted = False
    st.session_state.analysis_id = None
    st.session_state.saved_analysis_id = None
    st.session_state.current_image_b64 = ""
    st.session_state.demo_image_bytes = None
    st.session_state.save_error = None
    st.session_state.pop("uploader_nuevo", None)
    _reset_patient_fields()


def _render_navigation(result: dict) -> None:
    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        st.button(
            "Analizar otra imagen",
            icon=":material/refresh:",
            width="stretch",
            key="btn_otra_imagen",
            on_click=_clear_analysis,
        )
    with c2:
        st.button(
            "Nuevo paciente",
            icon=":material/person_add:",
            width="stretch",
            key="btn_nuevo_paciente",
            on_click=_reset_all,
        )
    if st.session_state.get("save_error"):
        st.warning(
            "El resultado se muestra, pero no se pudo guardar en la base local: "
            f"{st.session_state.save_error}",
            icon=":material/warning:",
        )
    if st.session_state.demo_mode:
        st.caption("Modo demostración: este resultado no se guardó en la base local.")
    elif result.get("status") != OOD_NO_ES_ECOGRAFIA:
        if st.session_state.get("saved_analysis_id"):
            st.caption("Resultado guardado en la base local de pacientes.")
        else:
            st.caption("El resultado no se guardó en la base local.")


def _render_result(result: dict) -> None:
    status = result.get("status")
    if status == OOD_NO_ES_ECOGRAFIA:
        _render_invalid(result)
    elif status == OOD_VALIDA_NO_CONCLUYENTE:
        _render_no_conclusive(result)
    elif status == OOD_VALIDA_CONFIABLE:
        _render_confident(result)
    else:
        st.error(
            "El resultado tiene un estado desconocido. No se muestra ninguna "
            "clase por seguridad.",
            icon=":material/error:",
        )
        _render_technical(result)

    _render_report_download(result)
    _render_navigation(result)


def view_nuevo_analisis(model, device) -> None:
    """Pinta la pestaña «Nuevo análisis»."""
    _init_tab_state()

    if not st.session_state.form_submitted:
        _render_progress(1)
        _render_patient_form()
        return

    _render_patient_summary()

    result = st.session_state.get("scan_results")
    if result:
        _render_progress(3)
        st.subheader("Paso 3 · Resultado del análisis")
        _render_result(result)
        return

    _render_progress(2)
    image_data = _render_image_upload()
    if image_data is None:
        return

    image, image_bytes = image_data
    st.divider()
    if st.button(
        "Analizar con IA",
        type="primary",
        width="stretch",
        icon=":material/play_circle:",
        key="btn_analizar",
    ):
        _run_analysis(model, device, image, image_bytes)
