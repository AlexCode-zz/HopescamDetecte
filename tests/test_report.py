"""Tests del reporte HTML: estados OOD, escape y datos ausentes."""

from __future__ import annotations

from hopescan.config import OOD_NO_ES_ECOGRAFIA, OOD_VALIDA_NO_CONCLUYENTE
from hopescan.report import create_report_content

PATIENT = {
    "nombres": "Ana",
    "apellidos": "Pérez",
    "edad": 30,
    "genero": "Femenino",
    "dui": "01234567-8",
}


def test_report_invalid_image_has_no_class():
    html = create_report_content(
        PATIENT,
        {
            "status": OOD_NO_ES_ECOGRAFIA,
            "result": None,
            "confidence": None,
            "probabilities_percent": None,
        },
    )
    assert "IMAGEN NO VÁLIDA" in html
    assert "Clase predicha: BENIGNO" not in html
    assert "Clase predicha: MALIGNO" not in html
    assert "No disponible" in html


def test_report_no_conclusive_has_no_forced_class():
    html = create_report_content(
        PATIENT,
        {
            "status": OOD_VALIDA_NO_CONCLUYENTE,
            "result": None,
            "confidence": None,
            "probabilities_percent": None,
        },
    )
    assert "NO CONCLUYENTE" in html
    assert "No se fuerza un resultado" in html
    assert "Clase predicha: NORMAL" not in html


def test_report_valid_class_includes_probabilities():
    html = create_report_content(
        PATIENT,
        {
            "status": "valida_confiable",
            "result": "Maligno",
            "confidence": 87.5,
            "probabilities_percent": [2.5, 87.5, 10.0],
            "temperature": 1.0,
        },
    )
    assert "MALIGNO" in html
    assert "87.50%" in html
    assert "2.50%" in html


def test_report_escapes_patient_html():
    html = create_report_content(
        {
            **PATIENT,
            "nombres": "<script>alert('x')</script>",
            "apellidos": "Pérez & Cía",
        },
        {
            "status": "valida_confiable",
            "result": "Normal",
            "confidence": 70.0,
            "probabilities_percent": [10.0, 20.0, 70.0],
        },
    )
    assert "<script>alert('x')</script>" not in html
    assert "&lt;script&gt;" in html
    assert "Pérez &amp; Cía" in html


def test_report_handles_invalid_probability_values():
    html = create_report_content(
        PATIENT,
        {
            "status": "valida_confiable",
            "result": "Benigno",
            "confidence": "N/A",
            "probabilities_percent": ["N/A", None, 10.0],
        },
    )
    assert "No disponible" in html
    assert "10.00%" in html


def test_report_empty_inputs():
    assert "ERROR" in create_report_content({}, {})
