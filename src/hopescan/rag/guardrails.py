"""Guardrails del chatbot: seguridad antes que fluidez.

Reglas duras (no las decide el LLM):

- Crisis emocional o autolesión → respuesta empática + ayuda inmediata.
- Síntomas urgentes → derivar a atención médica.
- Petición de diagnóstico → negarse y explicar.
- Petición de medicamentos o dosis → negarse.
- Prompt injection → ignorar la instrucción y seguir con el rol educativo.
- Fuera de tema → redirigir.

El texto recuperado y el mensaje del usuario son **datos**, nunca instrucciones.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .retriever import normalize

DISCLAIMER = (
    "HopeScan es una herramienta educativa de apoyo. No diagnostica, no receta "
    "y no sustituye la valoración de un profesional de la salud."
)

_CRISIS = re.compile(
    r"suicid|matarme|matar me|quitarme la vida|no quiero vivir|no quiero seguir viviendo|"
    r"autolesion|autolesionarme|hacerme dano|hacerme dano|desaparecer para siempre|"
    r"acabar con mi vida|terminar con mi vida",
)

_URGENT = re.compile(
    r"sangrado|sangre por el pezon|secrecion sanguinolenta|sangre espontanea|"
    r"bulto duro|bulto que crece|dolor intenso|dolor muy fuerte|fiebre|"
    r"piel de naranja|pezon invertido|pezon hundido|hundimiento del pezon|"
    r"enrojecimiento extenso|mama caliente|infeccion|pus",
)

_DIAGNOSIS = re.compile(
    r"^(tengo|es|sera) (un )?cancer|dime si (tengo|es) cancer|"
    r"puedes diagnosticar|diagnostica(me|r)?|confirmar (el )?diagnostico|"
    r"que tengo|es maligno|es benigno|tengo cancer|"
    r"puedo tener cancer|dime que tengo",
)

_MEDICATION = re.compile(
    r"dosis|cuantas pastillas|que medicamento|"
    r"receta(me|r)?|tomar .*mg|mg de|quimioterapia|tamoxifeno|"
    r"me puedo tomar|puedo tomar",
)

_INJECTION = re.compile(
    r"ignora (todas )?las instrucciones|ignore (all )?(previous|prior) instructions|"
    r"system prompt|prompt del sistema|revela.*(instrucciones|prompt)|"
    r"actua como|jailbreak|modo desarrollador|developer mode|"
    r"olvida tus reglas|olvida las reglas|haz de cuenta que",
)


@dataclass(frozen=True)
class GuardrailResult:
    """Resultado de un guardrail: categoría y respuesta segura."""

    kind: str
    message: str


def _matches(pattern: re.Pattern[str], text: str) -> bool:
    return bool(pattern.search(normalize(text)))


def detect_crisis(text: str) -> bool:
    return _matches(_CRISIS, text)


def detect_urgent(text: str) -> bool:
    return _matches(_URGENT, text)


def detect_diagnosis_request(text: str) -> bool:
    return _matches(_DIAGNOSIS, text)


def detect_medication_request(text: str) -> bool:
    return _matches(_MEDICATION, text)


def detect_prompt_injection(text: str) -> bool:
    return _matches(_INJECTION, text)


def check(text: str) -> GuardrailResult | None:
    """Evalúa los guardrails en orden de prioridad."""
    if not text or not text.strip():
        return GuardrailResult(
            kind="vacio",
            message="Escribe tu pregunta sobre prevención, síntomas, estudios o cómo interpretar un resultado.",
        )

    if detect_crisis(text):
        return GuardrailResult(
            kind="crisis",
            message=(
                "Siento mucho que estés pasando por esto. No estás solo o sola. "
                "Si tienes pensamientos de hacerte daño, busca ayuda ahora: habla con "
                "una persona de confianza, acude a un servicio de emergencia o llama "
                "al 911 si estás en peligro inmediato. También puedes contactar a una "
                "línea de apoyo en crisis de tu país. HopeScan no puede atender "
                "emergencias, pero mereces apoyo humano inmediato."
            ),
        )

    if detect_urgent(text):
        return GuardrailResult(
            kind="urgente",
            message=(
                "Lo que describes puede requerir una valoración médica pronta. "
                "No puedo valorar síntomas ni decirte qué tienes. Acude a un servicio "
                "de salud o a tu médico para un examen clínico. Si el sangrado es "
                "abundante, hay fiebre alta o el dolor es intenso, busca atención "
                "inmediata."
            ),
        )

    if detect_diagnosis_request(text):
        return GuardrailResult(
            kind="diagnostico",
            message=(
                "No puedo decirte si tienes o no tienes cáncer. HopeScan no "
                "diagnostica: solo orienta sobre patrones de imagen y puede equivocarse. "
                "Un diagnóstico requiere la valoración de un profesional de la salud, "
                "y a veces estudios como una biopsia. Si tienes una duda sobre tu "
                "resultado, llévalo a tu médico."
            ),
        )

    if detect_medication_request(text):
        return GuardrailResult(
            kind="medicamento",
            message=(
                "No puedo recomendar medicamentos, tratamientos ni dosis. Esa decisión "
                "corresponde a un profesional de la salud que conozca tu caso. Si estás "
                "en tratamiento, consulta con tu equipo médico antes de cambiar nada."
            ),
        )

    if detect_prompt_injection(text):
        return GuardrailResult(
            kind="inyeccion",
            message=(
                "No puedo cambiar mis instrucciones ni asumir otro papel. Puedo ayudarte "
                "con información educativa sobre el cáncer de mama, la prevención y cómo "
                "interpretar un resultado, siempre con la recomendación de consultar a un "
                "profesional."
            ),
        )

    return None


__all__ = [
    "DISCLAIMER",
    "GuardrailResult",
    "check",
    "detect_crisis",
    "detect_diagnosis_request",
    "detect_medication_request",
    "detect_prompt_injection",
    "detect_urgent",
]
