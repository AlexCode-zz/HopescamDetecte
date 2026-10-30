"""Generación del reporte HTML descargable (dependencia pura, sin Streamlit).

Hereda el HTML exacto del código original: misma estructura de estilos, mismo
flujo de ``result_value == 'Maligno'`` / ``'Normal'`` / ``Benigno``, mismo aviso
médico prominente. Se mantiene ``APP_NAME`` como fuente única para el footer.
"""

from __future__ import annotations

import base64
from datetime import datetime

import pandas as pd

from .config import APP_NAME


def create_report_content(patient_data: dict, scan_results: dict) -> str:
    """Genera el contenido del reporte descargable en formato HTML con los datos.

    ``patient_data``: {nombres, apellidos, edad, genero, dui, ...}
    ``scan_results``: {result, confidence, probabilities_percent, image_b64}
    """
    if not patient_data or not scan_results:
        return "ERROR: No hay datos de paciente o resultados de escaneo disponibles."

    probabilities = scan_results.get("probabilities_percent", [])
    prob_lines = "".join([
        f"<li><strong>{cls}:</strong> {p:.2f}%</li>"
        for cls, p in zip(["Benigno", "Maligno", "Normal"], probabilities)
    ])

    image_b64 = scan_results.get("image_b64", "") or ""
    image_tag = ""
    if image_b64:
        image_tag = f"""
            <div class="image-section">
                <h3>Imagen de Ultrasonido Analizada</h3>
                <img src="data:image/jpeg;base64,{image_b64}" alt="Imagen de Ultrasonido" class="ultrasound-image">
                <p><i>La imagen muestra el área analizada por el sistema de IA.</i></p>
            </div>
        """

    result_value = scan_results.get("result", "") or ""
    if result_value == "Maligno":
        result_class = "maligno"
        result_text_class = "maligno-text"
        recommendation_text = "ALTO RIESGO: Se recomienda CONSULTA MÉDICA ESPECIALIZADA URGENTE."
    elif result_value == "Normal":
        result_class = "normal"
        result_text_class = "normal-text"
        recommendation_text = "SIN HALLAZGOS: No se observan patrones de riesgo relevantes. Mantener controles preventivos habituales."
    else:
        # Asumimos Benigno por defecto
        result_class = ""
        result_text_class = "benigno-text"
        recommendation_text = "BAJO RIESGO: Se recomienda SEGUIMIENTO PROFESIONAL REGULAR."

    style = """
    <style>
        @page { size: A4; margin: 15mm; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 0; background-color: #f8f8f8; }
        .report-container {
            width: 100%; max-width: 210mm; margin: 20px auto; border: 1px solid #e0e0e0;
            box-shadow: 0 0 15px rgba(0,0,0,0.05); background-color: #ffffff; page-break-after: always;
        }
        .header-report { background-color: #2F3E46; color: white; padding: 20px 30px; text-align: center; border-bottom: 5px solid #F06292; }
        .header-report h1 { margin: 0; font-size: 1.8em; color: #ffffff; }
        .header-report p { margin: 5px 0 0; font-size: 0.9em; opacity: 0.9; }
        .content-section { padding: 25px 30px; }
        h2 { color: #F06292; border-bottom: 2px solid #F06292; padding-bottom: 8px; margin-top: 30px; font-size: 1.4em; }
        h3 { color: #3F51B5; font-size: 1.1em; margin-top: 20px; margin-bottom: 10px; }
        ul { list-style-type: none; padding-left: 0; margin-top: 10px; }
        ul li { margin-bottom: 8px; line-height: 1.5; color: #555; }
        ul li strong { color: #333; }
        .result-ia {
            background-color: #E8F5E9; border-left: 5px solid #4CAF50; padding: 15px;
            margin-top: 20px; border-radius: 5px;
        }
        .result-ia.maligno { background-color: #FFEBEE; border-left: 5px solid #F44336; }
        .result-ia.normal { background-color: #FFF8E1; border-left: 5px solid #FFC107; }
        .result-text { font-size: 1.3em; font-weight: bold; color: #333; }
        .maligno-text { color: #F44336; }
        .benigno-text { color: #4CAF50; }
        .normal-text { color: #BF360C; }
        .image-section { text-align: center; margin-top: 30px; padding: 15px; background-color: #f0f0f0; border-radius: 8px; }
        .ultrasound-image { max-width: 80%; height: auto; border: 1px solid #ccc; border-radius: 5px; margin-top: 10px; }
        .footer-report { text-align: center; margin-top: 40px; padding: 20px 30px; border-top: 1px solid #eee; color: #777; font-size: 0.85em; background-color: #fcfcfc; }
        .footer-report strong { color: #F06292; font-size: 1.1em; }
        .disclaimer { font-size: 0.8em; color: #999; margin-top: 20px; line-height: 1.4; border-top: 1px dashed #e0e0e0; padding-top: 15px; }
    </style>
    """

    content = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Reporte HopeScan - {patient_data.get('apellidos', '')}</title>
        {style}
    </head>
    <body>
        <div class="report-container">
            <div class="header-report">
                <h1>HopeScan IA</h1>
                <h2>Diagnóstico Automatizado de Cáncer de Mama</h2>
                <p>Fecha del Reporte: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>

            <div class="content-section">
                <h2>📋 Datos del Paciente</h2>
                <ul>
                    <li><strong>Nombres:</strong> {patient_data.get('nombres', 'N/A')}</li>
                    <li><strong>Apellidos:</strong> {patient_data.get('apellidos', 'N/A')}</li>
                    <li><strong>Edad:</strong> {patient_data.get('edad', 'N/A')} años</li>
                    <li><strong>Género:</strong> {patient_data.get('genero', 'N/A')}</li>
                    <li><strong>DUI:</strong> {patient_data.get('dui', 'N/A')}</li>
                </ul>

                {image_tag}

                <h2>🔎 Resultados del Escaneo por Inteligencia Artificial</h2>
                <div class="result-ia {result_class}">
                    <p class="result-text {result_text_class}">
                        Clase Predicha: {result_value.upper() if result_value else 'N/A'}
                    </p>
                    <p><strong>Nivel de Confianza:</strong> {scan_results.get('confidence', 'N/A')}%</p>
                    <p><strong>Recomendación del Sistema:</strong> {recommendation_text}</p>
                </div>

                <h3>📊 Distribución de Probabilidades</h3>
                <ul>{prob_lines}</ul>

                <div class="disclaimer">
                    <strong>⚠️ Aviso Importante:</strong> Este reporte es generado por un sistema de Inteligencia Artificial y tiene fines predictivos solamente. **NO SUSTITUYE, bajo ninguna circunstancia, el diagnóstico o la consulta con un profesional médico especialista (oncólogo o radiólogo). Se DEBE buscar confirmación clínica.** La interpretación final debe ser realizada por un profesional de la salud calificado.
                </div>
            </div>

            <div class="footer-report">
                <span>Generado por: <strong>{APP_NAME} IA</strong></span><br>
                <span>&copy; {datetime.now().year} Todos los derechos reservados.</span>
            </div>
        </div>
    </body>
    </html>
    """
    return content.strip()
