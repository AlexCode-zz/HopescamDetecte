"""Columna lateral (sidebar) con información y contactos médicos."""

from __future__ import annotations

import streamlit as st

ACERCA = "Acerca de esta aplicación"
CONTACTO_MEDICO = [
    (
        "Hospital Oncológico del ISSS",
        [
            "Teléfono: 2591-5000",
            "Dirección: San Salvador, entre la 25 Avenida Norte y la 1° Calle Poniente, frente a la estación de Bomberos y a un costado del Hospital Médico Quirúrgico.",
            "Horarios: lunes a viernes de 7:00 a.m. a 4:00 p.m.",
            "Web: https://www.isss.gob.sv/centros-de-atencion/",
        ],
    ),
    (
        "Centro Internacional de Cáncer (CIC)",
        [
            "Teléfono: +503 2506-2001",
            "Dirección: 3era Calle Poniente, Block No 122, Colonia Escalón, San Salvador.",
            "Horario: lunes a viernes, 8:00 a. m. - 5:00 p. m.",
            "Web: www.centrodecancer.com.sv",
        ],
    ),
    (
        "Instituto del Cáncer de El Salvador (ICES)",
        [
            "Dirección: Dr. Narciso Díaz Bazán, 1ª Calle Poniente y 33 Avenida Norte, Colonia Escalón, San Salvador.",
            "Horario: lunes a viernes de 6:30 a. m. a 3:30 p. m.",
            "Teléfono: +503 2521-8282 / 2521-8200",
            "Web: (no disponible)",
        ],
    ),
]
CANCER_INFO = """
El **cáncer de mama** es una enfermedad en la que las células de la mama crecen de forma descontrolada. Es el tipo de cáncer más común en mujeres a nivel mundial.

### Detección temprana (¡vital!)
La detección temprana es la mejor defensa. Si se detecta a tiempo, las tasas de supervivencia son muy altas. Los tres pilares son:

1. **Autoexamen:** revisar las mamas mensualmente para notar cambios.
2. **Examen clínico:** realizado por un profesional de la salud.
3. **Mamografía / ultrasonido:** estudios de imagen, recomendados anualmente según la edad y el riesgo.
"""
GUIDE = """
### Guía de uso rápida

1. **Llenar formulario:** completa los datos del paciente en "Nuevo análisis".
2. **Analizar y guardar:** sube la imagen y ejecuta el análisis. Los resultados se guardan automáticamente.
3. **Buscar:** usa "Buscar paciente" para consultar registros anteriores (requiere contraseña).
"""


def render_sidebar(title: str = ACERCA) -> None:
    """Pinta la columna lateral con información y contactos médicos."""
    st.title(title)

    st.error(
        title="Este análisis NO sustituye una consulta con un especialista",
        body="HopeScan es una herramienta de apoyo informativo. No reemplaza el diagnóstico médico.",
        icon=":material/health_and_safety:",
    )

    st.divider()

    for heading, bullets in CONTACTO_MEDICO:
        with st.container(border=True):
            st.subheader(heading, divider="gray")
            for b in bullets:
                st.markdown(f"- {b}")
            st.divider()

    with st.expander("Información general sobre el cáncer de mama", expanded=False):
        st.markdown(CANCER_INFO)

    with st.expander("Guía de uso rápida", expanded=False):
        st.markdown(GUIDE)

    st.divider()
    st.caption("HopeScan — El Salvador · Versión de apoyo diagnóstico")
