"""Contenido de la columna izquierda (acerca de, contacto médico, guía de uso).

Textos visibles heredados del código original (constantes conservadas).
"""

from __future__ import annotations

import streamlit as st

ACERCA = "Acerca de: Información y Contactos ℹ️"
CONTACTO_MEDICO = [
    (
        "🏥 Hospital Oncológico del ISSS",
        [
            "Teléfono: `2591-5000` ",
            "Dirección: San Salvador, entre la 25 Avenida Norte y la 1° Calle Poniente, justo frente a la estación de Bomberos y a un costado del Hospital Médico Quirúrgico, con entrada principal frente al Hospital Rosales",
            "Horarios (generales del ISSS): Lunes a viernes de 7:00 a.m. a 4:00 p.m. o 8:00 a.m. a 4:00 p.m.",
            "Dirección web: https://www.isss.gob.sv/centros-de-atencion/",
        ],
    ),
    (
        "🎗️ Centro Internacional de Cáncer (CIC)",
        [
            "Teléfono: `+503 2506-2001`",
            "3era Calle Poniente, Block No 122 Colonia Escalón, San Salvador, San Salvador, El Salvador",
            "Horario: Lunes a Viernes, 8:00 AM - 5:00 PM.",
            "Dirección web: www.centrodecancer.com.sv.",
        ],
    ),
    (
        "⚖️ Instituto del Cáncer de El Salvador (ICES)",
        [
            "Direccion: Dr. Narciso Díaz Bazán, es la 1ª Calle Poniente y 33 Avenida Norte, Colonia Escalón, San Salvador",
            "Horario: Lunes a Viernes de 6:30 a.m. a 3:30 p.m.",
            "Teléfono: `+503 2521-8282` `2521-8200`",
            "Dirección web: ",
        ],
    ),
]
CANCER_INFO = """
El **Cáncer de Mama** es una enfermedad en la que las células de la mama crecen de forma descontrolada. Es el tipo de cáncer más común en mujeres a nivel mundial.

### 🔬 Detección Temprana (¡Vital!)
La detección temprana es la mejor defensa. Si se detecta a tiempo, las tasas de supervivencia son muy altas. Los tres pilares de la detección son:

1.  **Autoexamen:** Revisar tus mamas mensualmente para notar cambios.
2.  **Examen Clínico:** Realizado por un profesional de la salud.
3.  **Mamografía/Ultrasonido:** Estudios de imagen, recomendados anualmente a partir de cierta edad (varía según el riesgo).
"""
GUIDE = """
Sigue estos pasos:
#### 1. Llenar Formulario
Completa los datos del paciente en la pestaña **'Nuevo Análisis'**.
#### 2. Analizar y Guardar
Sube la imagen y realiza el análisis. Los resultados se guardarán automáticamente.
#### 3. Buscar (Requiere Contraseña)
Usa la pestaña **'Buscar Paciente'** para consultar registros anteriores.
"""


def render_sidebar(title: str = ACERCA) -> None:
    """Pinta la columna izquierda con información y contactos médicos."""
    with st.expander(title, expanded=True):
        st.subheader("⚠️ Este análisis NO sustituye una consulta con un especialista.")
        st.markdown("---")

        for heading, bullets in CONTACTO_MEDICO:
            with st.expander(heading, expanded=False):
                for b in bullets:
                    st.markdown(f"*{b}*")
                st.markdown("---")

        with st.expander(
            "🧠 Información General sobre el Cáncer de Mama", expanded=False
        ):
            st.markdown(CANCER_INFO)

        with st.expander("⚙️ Guía de Uso Rápido de la Aplicación", expanded=False):
            st.markdown(GUIDE)
