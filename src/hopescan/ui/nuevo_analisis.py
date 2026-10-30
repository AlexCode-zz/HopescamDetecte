"""Contenido de la pestaña 'Nuevo Análisis': formulario + imagen + resultados."""

from __future__ import annotations

import base64
from io import BytesIO

import streamlit as st
from PIL import Image
import pandas as pd

from ..inference import predict_image
from ..patients import validate_patient_form, save_patient_data
from ..report import create_report_content

CONFIDENCE_WARN_THRESHOLD = 60.0  # FASE 3:Advertencia cuando confianza baja sin alterar el resultado mostrado


def view_nuevo_analisis(model, device) -> None:
    """Pinta la pestaña 'Nuevo Análisis'.

    Mantiene el flujo exacto del código original: formulario -> upload ->
    predicción -> guardado -> descarga HTML. Añade FASE 3 (warn de baja
    confianza sin modificar resultado mostrado; conversión RGB estricta).
    """
    if not st.session_state.form_submitted:
        st.markdown('<div class="patient-form-container">', unsafe_allow_html=True)
        st.subheader("📝 1. Registro Obligatorio del Paciente")

        with st.form(key='patient_form'):
            nombres = st.text_input("Nombres del Paciente (Obligatorio)", key='nombres_input')
            apellidos = st.text_input("Apellidos del Paciente (Obligatorio)", key='apellidos_input')
            edad = st.number_input("Edad del Paciente (Años)", min_value=0, max_value=120, value=30, step=1, key='edad_input')
            genero = st.selectbox("Género", ["Femenino"], key='genero_input')
            dui = ""
            if edad >= 18:
                dui = st.text_input("DUI (Documento Único de Identidad) - Obligatorio para mayores de 18", placeholder="Ej: 01234567-8", key='dui_input')
            submit_button = st.form_submit_button(label='✅ Guardar Datos e Ir al Análisis', type="primary")

            if submit_button:
                err = validate_patient_form(nombres=nombres, apellidos=apellidos, edad= edad, dui=dui)
                if err is not None:
                    st.error(err)
                elif edad < 18:
                    pass  # DUI fuente tetap ""; se guarda 'Menor de 18' en build_record
                else:
                    st.session_state.patient_data = {'nombres': nombres, 'apellidos': apellidos, 'edad': edad, 'genero': genero, 'dui': dui if edad >= 18 else 'Menor de 18'}
                    st.session_state.form_submitted = True
                    st.success("Datos del paciente guardados. ¡Ahora puede proceder con el análisis de imagen!")
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    if not st.session_state.form_submitted:
        st.info("Comienza llenando el formulario de registro obligatorio del paciente.")
        return

    st.info(f"Paciente actual: **{st.session_state.patient_data['nombres']} {st.session_state.patient_data['apellidos']}** ({st.session_state.patient_data['edad']} años)")

    st.subheader("📸 2. Subida de Imagen de Ultrasonido")
    uploaded_file = st.file_uploader("Sube una imagen de ultrasonido (.png, .jpg, .jpeg)", type=["png", "jpg", "jpeg"], key="uploader_nuevo")

    image_to_analyze = None
    if uploaded_file is not None:
        try:
            img = Image.open(uploaded_file).convert("RGB")
        except Exception as exc:  # FASE 3: manejamos imagen corrupta/inválida
            st.error(f"❌ La imagen no pudo ser cargada: {exc}")
            return
        image_to_analyze = img
        st.image(image_to_analyze, caption="Imagen de Ultrasonido Subida", use_container_width=True)

        buffered = BytesIO()
        try:
            image_to_analyze.save(buffered, format="JPEG")
            image_b64 = base64.b64encode(buffered.getvalue()).decode()
        except Exception as exc:  # FASE 3: conversión a base64 falló
            st.error(f"❌ Error al convertir la imagen a base64: {exc}")
            return

        if st.session_state.scan_results is None:
            st.session_state.scan_results = {}
        st.session_state.scan_results['image_b64'] = image_b64

        st.subheader("🚀 3. Análisis Predictivo")
        if st.button("🚀 Iniciar Análisis Predictivo", use_container_width=True, key="btn_analizar"):
            # Limpiar resultados anteriores (excepto la imagen Base64) -> evita doble guardado en reruns
            current_image_b64 = st.session_state.scan_results.get('image_b64', '')
            st.session_state.scan_results = {'image_b64': current_image_b64}

            with st.spinner("Analizando imagen con MobileNetV2..."):
                pred_idx, probs = predict_image(model, device, image_to_analyze)

            if pred_idx is None:
                st.warning("⚠️ No se pudo obtener el diagnóstico. Revisa el log de errores.")
                return

            resultado = ["Benigno", "Maligno", "Normal"][pred_idx]
            confianza = probs[pred_idx] * 100

            scan_results = {'result': resultado, 'confidence': f"{confianza:.2f}", 'probabilities_percent': [p * 100 for p in probs], 'image_b64': image_b64}
            st.session_state.scan_results.update(scan_results)

            # FASE 3: evitar guardar el mismo análisis dos veces en un rerun
            # (current_dui == dui del paciente actual -> ya se guardó)
            if st.session_state.current_dui != st.session_state.patient_data['dui']:
                save_patient_data(st.session_state.patient_data, scan_results)
                st.session_state.current_dui = st.session_state.patient_data['dui']

            st.subheader("✅ 4. Resultados del Diagnóstico por IA")

            if resultado == "Maligno":
                st.error("🔴 HALLAZGO CLASIFICADO COMO: MALIGNO o SOSPECHOSO")
                st.write("La IA sugiere que las características de la imagen son compatibles con un patrón de alto riesgo. **Consulte a su médico de inmediato.**")
            elif resultado == "Benigno":
                st.info("🟢 HALLAZGO CLASIFICADO COMO: BENIGNO")
                st.write("La IA sugiere que la imagen es compatible con un patrón de bajo riesgo. **Siempre se recomienda la revisión profesional.**")
            else:
                st.success("🔵 HALLAZGO CLASIFICADO COMO: NORMAL / SIN HALLAZGOS")
                st.write("La IA no detectó características sugestivas de riesgo. Mantener controles preventivos habituales y consulte a su médico si aparece algún síntoma o duda.")

            # FASE 3: advertencia baja confianza sin alterar resultado mostrado
            if confianza < CONFIDENCE_WARN_THRESHOLD and confianza > 0:
                st.warning(f"⚠️ Nivel de confianza bajo ({confianza:.2f}%). Este valor NO reemplaza al mostrado y el diagnóstico sigue vigente. Revisión médica recomendada.")

            st.markdown("---")
            st.metric(label=f"Clase Predicha", value=resultado.upper(), delta=f"{confianza:.2f}% de Confianza")

            prob_data = {"Clase": ["Benigno", "Maligno", "Normal"], "Probabilidad (%)": [p * 100 for p in probs]}
            df_prob = pd.DataFrame(prob_data)
            st.bar_chart(df_prob, x='Clase', y='Probabilidad (%)', height=250)

    if uploaded_file is None:
        st.info("Sube una imagen de ultrasonido para iniciar el análisis. Los resultados y el botón de descarga aparecerán aquí.")

    # Descarga de reporte HTML
    if st.session_state.scan_results and st.session_state.scan_results.get('result') is not None:
        report_content = create_report_content(st.session_state.patient_data, st.session_state.scan_results)
        st.markdown("---")
        st.subheader("💾 Descargar Reporte (Paso Final)")
        st.download_button(label="⬇️ Descargar Reporte en formato HTML", data=report_content, file_name=f"Reporte_{st.session_state.patient_data['apellidos']}_{st.session_state.current_dui}.html", mime="text/html", use_container_width=True, type="primary")

        report_b64 = base64.b64encode(report_content.encode('utf-8')).decode('utf-8')
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
        if st.button("🖨️ Abrir Reporte en Ventana de Impresión (Recomendado para PDF)", use_container_width=True, key="btn_imprimir"):
            st.markdown(f'<script>openPrintWindow();</script>', unsafe_allow_html=True)

        if st.button("🔄 Registrar Nuevo Paciente", use_container_width=True, key="btn_nuevo"):
            st.session_state.form_submitted = False
            st.session_state.patient_data = {}
            st.session_state.scan_results = None
            st.session_state.current_dui = None
            st.rerun()
