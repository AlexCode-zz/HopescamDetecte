"""Columna lateral: estado, guía, privacidad y contactos médicos."""

from __future__ import annotations

import streamlit as st

from ..config import APP_DISCLAIMER, APP_TAGLINE, load_ood_config
from ..rag.chat import llm_available

ACERCA = "HopeScan"
CONTACTO_MEDICO = [
    (
        "Hospital Oncológico del ISSS",
        [
            "Teléfono: 2591-5000",
            "Dirección: San Salvador, entre la 25 Avenida Norte y la 1.ª Calle Poniente.",
            "Horario: lunes a viernes, 7:00 a. m. – 4:00 p. m.",
            "Web: https://www.isss.gob.sv/centros-de-atencion/",
        ],
    ),
    (
        "Centro Internacional de Cáncer (CIC)",
        [
            "Teléfono: +503 2506-2001",
            "Dirección: 3.ª Calle Poniente, Block 122, Colonia Escalón, San Salvador.",
            "Horario: lunes a viernes, 8:00 a. m. – 5:00 p. m.",
            "Web: https://www.centrodecancer.com.sv",
        ],
    ),
    (
        "Instituto del Cáncer de El Salvador (ICES)",
        [
            "Dirección: Dr. Narciso Díaz Bazán, 1.ª Calle Poniente y 33 Avenida Norte, Colonia Escalón, San Salvador.",
            "Horario: lunes a viernes, 6:30 a. m. – 3:30 p. m.",
            "Teléfono: +503 2521-8282 / 2521-8200",
        ],
    ),
]

CANCER_INFO = """
El **cáncer de mama** es una enfermedad en la que las células de la mama crecen
de forma descontrolada. Es el tipo de cáncer más frecuente en mujeres a nivel
mundial.

### Detección temprana

1. **Autoexamen:** conocer cómo se ven y se sienten las mamas para notar cambios.
2. **Examen clínico:** realizado por un profesional de la salud.
3. **Mamografía / ultrasonido:** estudios de imagen según la edad y el riesgo.

La detección temprana mejora las opciones de tratamiento, pero ninguna prueba
por sí sola confirma o descarta cáncer.
"""

GUIDE = """
### Guía de uso

1. **Paciente:** completa los datos mínimos y confirma la autorización.
2. **Imagen:** sube una ecografía en escala de grises o usa la demostración.
3. **Resultado:** lee el estado. Si la imagen no es válida o el análisis no es
   concluyente, **no se muestra ninguna clase**.
4. **Reporte:** descarga el HTML y llévalo a tu consulta médica.
"""


def _render_status(model_ready: bool, device: str | None) -> None:
    calibration = load_ood_config()
    with st.container(border=True):
        st.markdown("#### Estado del sistema")
        c1, c2 = st.columns(2)
        with c1:
            if model_ready:
                st.badge("Modelo listo", icon=":material/check_circle:", color="green")
            else:
                st.badge("Modelo no disponible", icon=":material/error:", color="red")
        with c2:
            st.badge(
                f"OOD {calibration.get('calibration_status', 'activo')}",
                icon=":material/verified_user:",
                color="blue",
            )
        st.caption(
            f"Dispositivo: **{device or 'no disponible'}** · "
            f"Calibración: `{calibration.get('version', 'desconocida')}`"
        )
        if llm_available():
            st.badge("Chat con Claude", icon=":material/smart_toy:", color="violet")
        else:
            st.badge(
                "Chat local con citas",
                icon=":material/menu_book:",
                color="gray",
            )


def render_sidebar(
    title: str = ACERCA,
    *,
    model_ready: bool = True,
    device: str | None = None,
) -> None:
    """Pinta la columna lateral con estado, información y contactos."""
    st.title(title)
    st.caption(APP_TAGLINE)
    st.badge("Herramienta educativa", icon=":material/school:", color="violet")

    st.divider()
    _render_status(model_ready, device)

    st.warning(
        title="No es un dispositivo médico",
        body=APP_DISCLAIMER,
        icon=":material/health_and_safety:",
    )

    with st.expander("Cómo funciona", expanded=False):
        st.markdown(
            "1. **Validación:** comprobamos que la imagen parezca una ecografía "
            "mamaria en escala de grises.\n"
            "2. **Análisis:** MobileNetV2 calcula la clase y la confianza "
            "calibrada.\n"
            "3. **Decisión:** si la imagen no es válida, no se muestra ninguna "
            "clase. Si el modelo no tiene certeza, el resultado es **no "
            "concluyente**. Solo se muestra una clase cuando el estado es "
            "**válido y confiable**.\n"
            "4. **Explicación:** el Grad-CAM indica dónde se fijó el modelo; no "
            "señala una lesión."
        )

    with st.expander("Información sobre el cáncer de mama", expanded=False):
        st.markdown(CANCER_INFO)

    with st.expander("Directorio de contacto", expanded=False):
        for heading, bullets in CONTACTO_MEDICO:
            with st.container(border=True):
                st.markdown(f"**{heading}**")
                for bullet in bullets:
                    st.markdown(f"- {bullet}")

    with st.expander("Privacidad y datos", expanded=False):
        st.markdown(
            "- Los datos del paciente y los resultados se guardan en un CSV "
            "local (`data/patient_records.csv`), fuera de Git.\n"
            "- Las imágenes no se guardan en el CSV; se procesan en memoria.\n"
            "- El DUI se muestra enmascarado en la búsqueda.\n"
            "- Si configuras Claude, la pregunta del chat y los fragmentos "
            "recuperados se envían a la API de Anthropic. Las imágenes nunca se "
            "envían al chat.\n"
            "- No subas datos de otra persona sin su consentimiento. Para "
            "menores de edad se requiere autorización del tutor."
        )

    with st.expander("Guía de uso rápida", expanded=False):
        st.markdown(GUIDE)

    st.divider()
    st.caption("HopeScan · El Salvador · Herramienta de apoyo educativo")
