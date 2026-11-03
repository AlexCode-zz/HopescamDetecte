"""Generación del reporte HTML descargable (sin Streamlit).

El reporte es un documento de **apoyo**, no un diagnóstico. Incluye el estado
OOD, la confianza calibrada, la imagen analizada, el Grad-CAM (si existe) y el
aviso médico. Todos los campos de texto se escapan para evitar inyección HTML.
"""

from __future__ import annotations

import html
from datetime import datetime

from .config import (
    APP_NAME,
    OOD_NO_ES_ECOGRAFIA,
    OOD_VALIDA_CONFIABLE,
    OOD_VALIDA_NO_CONCLUYENTE,
)


def _escape(value: object) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def _safe_image(b64: str | None) -> str:
    """Valida que el base64 solo contenga caracteres seguros."""
    if not b64:
        return ""
    allowed = set(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=\n\r"
    )
    if any(char not in allowed for char in b64):
        return ""
    return b64.strip()


def create_report_content(patient_data: dict, scan_results: dict) -> str:
    """Genera el HTML del reporte descargable.

    ``patient_data``: ``nombres``, ``apellidos``, ``edad``, ``genero``, ``dui``.
    ``scan_results``: ``status``, ``result``, ``confidence``,
    ``probabilities_percent``, ``image_b64``, ``gradcam_b64``.
    """
    if not patient_data or not scan_results:
        return "ERROR: No hay datos de paciente o resultados de escaneo disponibles."

    probabilities = scan_results.get("probabilities_percent") or []
    prob_lines = ""
    for cls, value in zip(["Benigno", "Maligno", "Normal"], probabilities):
        try:
            formatted = f"{float(value):.2f}%"
        except (TypeError, ValueError):
            formatted = "No disponible"
        prob_lines += f"<li><strong>{_escape(cls)}:</strong> {formatted}</li>"

    image_b64 = _safe_image(scan_results.get("image_b64"))
    image_tag = ""
    if image_b64:
        image_tag = f"""
            <div class="image-section">
                <h3>Imagen de ultrasonido analizada</h3>
                <img src="data:image/jpeg;base64,{image_b64}" alt="Imagen de ultrasonido analizada" class="ultrasound-image">
                <p><i>La imagen se muestra solo para contextualizar el resultado.</i></p>
            </div>
        """

    gradcam_b64 = _safe_image(scan_results.get("gradcam_b64"))
    gradcam_tag = ""
    if gradcam_b64:
        gradcam_tag = f"""
            <div class="image-section">
                <h3>Explicación visual (Grad-CAM)</h3>
                <img src="data:image/jpeg;base64,{gradcam_b64}" alt="Mapa de calor Grad-CAM sobre la ecografía" class="ultrasound-image">
                <p><i>Las zonas cálidas indican dónde se fijó el modelo. No son una lesión ni un diagnóstico.</i></p>
            </div>
        """

    status = scan_results.get("status")
    result_value = scan_results.get("result") or ""
    confidence = scan_results.get("confidence")

    if status == OOD_NO_ES_ECOGRAFIA:
        result_class = "no-concluyente"
        result_text_class = "no-concluyente-text"
        result_label = "IMAGEN NO VÁLIDA"
        recommendation_text = (
            "No se emitió ninguna clase ni porcentaje porque la imagen no parece "
            "una ecografía mamaria. Sube una imagen de ultrasonido de mama."
        )
    elif status == OOD_VALIDA_NO_CONCLUYENTE or not result_value:
        result_class = "no-concluyente"
        result_text_class = "no-concluyente-text"
        result_label = "NO CONCLUYENTE"
        recommendation_text = (
            "El modelo no tiene certeza suficiente. No se fuerza un resultado. "
            "Consulta a un especialista y, si es posible, repite la ecografía."
        )
    elif result_value == "Maligno":
        result_class = "maligno"
        result_text_class = "maligno-text"
        result_label = "MALIGNO"
        recommendation_text = (
            "HALLAZGO SOSPECHOSO: se recomienda consulta médica especializada "
            "prioritaria. Este resultado NO es un diagnóstico."
        )
    elif result_value == "Normal":
        result_class = "normal"
        result_text_class = "normal-text"
        result_label = "NORMAL"
        recommendation_text = (
            "SIN HALLAZGOS: no se observan patrones de riesgo relevantes. "
            "Mantén los controles preventivos habituales."
        )
    else:
        result_class = "benigno"
        result_text_class = "benigno-text"
        result_label = "BENIGNO"
        recommendation_text = (
            "BAJO RIESGO: se recomienda seguimiento profesional regular. "
            "Este resultado NO es un diagnóstico."
        )

    try:
        confidence_text = f"{float(confidence):.2f}%"
    except (TypeError, ValueError):
        confidence_text = "No disponible"
    result_prefix = (
        "Clase predicha"
        if status == OOD_VALIDA_CONFIABLE and result_value
        else "Estado del análisis"
    )
    temperature = scan_results.get("temperature")
    calibration_note = (
        f"Confianza calibrada (temperatura T={float(temperature):.2f})."
        if temperature is not None
        else "Confianza del modelo."
    )

    disclaimer = (
        "Este reporte es generado por un sistema de Inteligencia Artificial y "
        "tiene fines educativos y de apoyo. <strong>NO SUSTITUYE, bajo ninguna "
        "circunstancia, el diagnóstico o la consulta con un profesional médico "
        "especialista (oncólogo o radiólogo). Se DEBE buscar confirmación clínica.</strong> "
        "La interpretación final debe ser realizada por un profesional de la salud "
        "calificado. El modelo no está certificado como dispositivo médico."
    )

    content = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Reporte {_escape(APP_NAME)} — {_escape(patient_data.get("apellidos", ""))}</title>
        <style>
            @page {{ size: A4; margin: 15mm; }}
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 0; background-color: #f8fafc; color: #1f2937; }}
            .report-container {{ width: 100%; max-width: 210mm; margin: 20px auto; border: 1px solid #e5e7eb; box-shadow: 0 0 15px rgba(0,0,0,0.05); background-color: #ffffff; }}
            .header-report {{ background: linear-gradient(135deg, #831843, #db2777); color: white; padding: 24px 30px; text-align: center; }}
            .header-report h1 {{ margin: 0; font-size: 1.8em; }}
            .header-report p {{ margin: 6px 0 0; font-size: 0.9em; opacity: 0.95; }}
            .content-section {{ padding: 25px 30px; }}
            h2 {{ color: #be185d; border-bottom: 2px solid #fbcfe8; padding-bottom: 8px; margin-top: 30px; font-size: 1.3em; }}
            h3 {{ color: #374151; font-size: 1.05em; margin-top: 20px; margin-bottom: 10px; }}
            ul {{ list-style-type: none; padding-left: 0; margin-top: 10px; }}
            ul li {{ margin-bottom: 8px; line-height: 1.5; color: #4b5563; }}
            ul li strong {{ color: #111827; }}
            .result-ia {{ background-color: #ecfdf5; border-left: 5px solid #10b981; padding: 16px; margin-top: 20px; border-radius: 8px; }}
            .result-ia.maligno {{ background-color: #fef2f2; border-left-color: #ef4444; }}
            .result-ia.normal {{ background-color: #eff6ff; border-left-color: #3b82f6; }}
            .result-ia.no-concluyente {{ background-color: #fffbeb; border-left-color: #f59e0b; }}
            .result-text {{ font-size: 1.25em; font-weight: 700; color: #111827; }}
            .maligno-text {{ color: #b91c1c; }}
            .benigno-text {{ color: #047857; }}
            .normal-text {{ color: #1d4ed8; }}
            .no-concluyente-text {{ color: #92400e; }}
            .image-section {{ text-align: center; margin-top: 24px; padding: 15px; background-color: #f8fafc; border-radius: 8px; }}
            .ultrasound-image {{ max-width: 80%; height: auto; border: 1px solid #e5e7eb; border-radius: 6px; margin-top: 10px; }}
            .footer-report {{ text-align: center; margin-top: 40px; padding: 20px 30px; border-top: 1px solid #f3f4f6; color: #6b7280; font-size: 0.85em; background-color: #fcfcfc; }}
            .footer-report strong {{ color: #db2777; font-size: 1.1em; }}
            .disclaimer {{ font-size: 0.8em; color: #6b7280; margin-top: 20px; line-height: 1.5; border-top: 1px dashed #e5e7eb; padding-top: 15px; }}
        </style>
    </head>
    <body>
        <div class="report-container">
            <div class="header-report">
                <h1>{_escape(APP_NAME)} IA</h1>
                <h2>Reporte de apoyo al análisis de ecografía mamaria</h2>
                <p>Fecha del reporte: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
            </div>

            <div class="content-section">
                <h2>Datos del paciente</h2>
                <ul>
                    <li><strong>Nombres:</strong> {_escape(patient_data.get("nombres", "N/A"))}</li>
                    <li><strong>Apellidos:</strong> {_escape(patient_data.get("apellidos", "N/A"))}</li>
                    <li><strong>Edad:</strong> {_escape(patient_data.get("edad", "N/A"))} años</li>
                    <li><strong>Género:</strong> {_escape(patient_data.get("genero", "N/A"))}</li>
                    <li><strong>DUI:</strong> {_escape(patient_data.get("dui", "N/A"))}</li>
                </ul>

                {image_tag}
                {gradcam_tag}

                <h2>Resultado del análisis por inteligencia artificial</h2>
                <div class="result-ia {result_class}">
                    <p class="result-text {result_text_class}">
                        {result_prefix}: {_escape(result_label)}
                    </p>
                    <p><strong>Nivel de confianza:</strong> {_escape(confidence_text)}</p>
                    <p><strong>Recomendación del sistema:</strong> {_escape(recommendation_text)}</p>
                </div>
                <p><i>{_escape(calibration_note)}</i></p>

                <h3>Distribución de probabilidades</h3>
                <ul>{prob_lines or "<li>No disponible: el resultado no es concluyente.</li>"}</ul>

                <div class="disclaimer">
                    <strong>Aviso importante:</strong> {disclaimer}
                </div>
            </div>

            <div class="footer-report">
                <span>Generado por: <strong>{_escape(APP_NAME)} IA</strong></span><br>
                <span>&copy; {datetime.now().year} Todos los derechos reservados.</span>
            </div>
        </div>
    </body>
    </html>
    """
    return content.strip()
