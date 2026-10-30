"""Un solo motor de respuestas para el chatbot.

Fusiona TODAS las respuestas útiles de las tres implementaciones duplicadas
del código original (`responder()` a lo largo de línea 808, 1004, 1061) en
un diccionario de reglas con coincidencia tolerante a tildes y mayúsculas.
"""

from __future__ import annotations

import re

# Coincidencia tolerante a tildes / mayúsculas -> pattern de substring corta.
# Ordenados por longitud descendente para evitar cortocircuitos por chunks menores.
REGISTROS_ECO: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(r"que es ecoscan|qué es ecoscan|que es el eco", re.IGNORECASE),
        "EcoScan es una herramienta diseñada para analizar patrones relacionados con el cáncer de mama mediante inteligencia artificial. No reemplaza a un médico, pero sirve como apoyo informativo para la detección temprana y la educación preventiva.",
    ),
    (
        re.compile(r"hola|buenos días|buenas|qué tal|hi|hey|hello", re.IGNORECASE),
        "Hola, soy el asistente de HopeScan. ¿Qué deseas saber?",
    ),
    (
        re.compile(
            r"que hago si tengo miedo|tengo miedo|tenho medo|miedo", re.IGNORECASE
        ),
        "Es completamente normal sentir miedo ante resultados médicos. Lo más importante es no quedarse con la duda y acudir a un especialista. Recuerda que la mayoría de hallazgos resultan benignos, y mientras más temprano consultes, más opciones y tranquilidad tendrás.",
    ),
    (
        re.compile(r"síntomas|sintomas| síntomas", re.IGNORECASE),
        "Algunos síntomas que pueden alertar incluyen: bultos en el seno o axila, cambios en la piel, secreción anormal del pezón o dolor persistente. Sin embargo, muchos casos no presentan síntomas, por eso los chequeos periódicos son fundamentales.",
    ),
    (
        re.compile(
            r"que hago ahora|que puedo hacer ahora|qué hacer ahora|qué hago|qué tengo",
            re.IGNORECASE,
        ),
        "Lo ideal es consultar a un médico especialista. Lleva la información del análisis, tus antecedentes y cualquier síntoma que hayas notado. Un profesional podrá guiarte con estudios como mamografías, ultrasonidos o una biopsia si fuera necesario.",
    ),
    (
        re.compile(r"riesgos|riesgo|por qué es peligroso", re.IGNORECASE),
        "Los principales factores de riesgo incluyen: antecedentes familiares, edad mayor a 40 años, cambios genéticos (BRCA1/BRCA2), obesidad, tabaquismo, alcohol, y sedentarismo. Sin embargo, cualquier persona puede presentar alteraciones, por eso la prevención es clave.",
    ),
    (
        re.compile(
            r"importancia del chequeo|por qué es importante|por qué es importante la detección",
            re.IGNORECASE,
        ),
        "Los chequeos permiten detectar alteraciones antes de que aparezcan síntomas, lo que aumenta significativamente las probabilidades de tratamiento exitoso. La detección temprana salva vidas.",
    ),
    (
        re.compile(r"como prevenir|prevencion|prevención", re.IGNORECASE),
        "Algunas medidas preventivas incluyen: mantener un peso saludable, hacer ejercicio, evitar fumar, limitar el alcohol, realizar autoexámenes mensuales y acudir a mamografías según la edad y recomendaciones médicas.",
    ),
    (
        re.compile(r"autoexamen|auto examen", re.IGNORECASE),
        "El autoexamen consiste en revisar tus senos una vez al mes para identificar cambios o bultos. Debe hacerse de pie, acostada y frente al espejo. Si encuentras algo inusual, consulta con un profesional.",
    ),
    (
        re.compile(r"mamografia|mamografía", re.IGNORECASE),
        "La mamografía es un estudio de imagen que detecta alteraciones muy pequeñas antes de que puedan sentirse físicamente. Es recomendada en mujeres mayores de 40 años, o antes si existen factores de riesgo.",
    ),
    (
        re.compile(r"ultrasonido", re.IGNORECASE),
        "El ultrasonido de mama es un estudio complementario que ayuda a diferenciar entre quistes y masas sólidas. Es útil en personas jóvenes o con tejido mamario denso.",
    ),
    (
        re.compile(r"biopsia", re.IGNORECASE),
        "La biopsia consiste en tomar una pequeña muestra de tejido para analizarla en laboratorio. Es el método más preciso para confirmar si una masa es benigna o maligna.",
    ),
    (
        re.compile(r"que significa patrón", re.IGNORECASE),
        "Un 'patrón' es la forma, densidad o estructura que el sistema identifica en la imagen analizada. Algunos patrones sugieren benignidad y otros requieren revisión médica más detallada.",
    ),
    (
        re.compile(
            r"por que consultar a un medico|por qué consultar|qué consultar",
            re.IGNORECASE,
        ),
        "Porque EcoScan no da diagnósticos. Solo un especialista puede confirmar la naturaleza de un hallazgo mediante estudios clínicos. Consultar a tiempo evita complicaciones y mejora los resultados.",
    ),
    (
        re.compile(r"gracias|muchas gracias|thank you", re.IGNORECASE),
        "Con gusto, estoy aquí para apoyarte. Si necesitas más información o tienes dudas sobre prevención, síntomas o resultados, pregúntame.",
    ),
    (
        re.compile(r"dolor|me duele|duele", re.IGNORECASE),
        "El dolor en el seno no siempre está relacionado con cáncer. Puede deberse a cambios hormonales, quistes, inflamaciones o tensión muscular. Sin embargo, si el dolor es persistente o viene acompañado de un bulto, consulta a un médico.",
    ),
    (
        re.compile(r"bulto|bola|tumor", re.IGNORECASE),
        "Encontrar un bulto puede ser preocupante, pero la mayoría son benignos. Algunos pueden ser quistes o fibroadenomas. Aún así, es recomendable visitar a un médico para una evaluación completa.",
    ),
    (
        re.compile(r"secrecion|líquido|lactancia", re.IGNORECASE),
        "La secreción del pezón puede tener varias causas: infecciones, cambios hormonales, medicamentos o, en casos raros, cáncer de mama. Si la secreción es sanguinolenta o espontánea, consulta a un especialista.",
    ),
    (
        re.compile(r"cambio.*piel|piel.*cambio|cambios en la piel", re.IGNORECASE),
        "Cambios en la piel como enrojecimiento, hundimientos, textura de 'piel de naranja' o inflamación pueden requerir evaluación médica. Son señales que deben observarse con atención.",
    ),
    (
        re.compile(r"factores|causas|razones", re.IGNORECASE),
        "Los factores de riesgo más comunes incluyen edad avanzada, antecedentes familiares, mutaciones genéticas, hábitos como tabaquismo y alcohol, y estilos de vida sedentarios. No obstante, cualquier persona puede desarrollar alteraciones aun sin factores de riesgo.",
    ),
    (
        re.compile(r"tratamiento", re.IGNORECASE),
        "El tratamiento del cáncer de mama depende del diagnóstico final y puede incluir cirugía, radioterapia, quimioterapia, terapias hormonales o terapias dirigidas. El especialista determinará el mejor plan según cada caso.",
    ),
    (
        re.compile(r"curar|cura|curación", re.IGNORECASE),
        "El cáncer de mama detectado a tiempo tiene tasas de curación muy altas. La detección temprana mejora significativamente las posibilidades de un tratamiento exitoso.",
    ),
    (
        re.compile(r"probabilidad|porcentaje", re.IGNORECASE),
        "Las probabilidades dependen de múltiples factores: tipo de lesión, antecedentes, edad, y estudios clínicos. El análisis de EcoScan no da porcentajes de diagnóstico, solo ayuda a identificar patrones que deben revisarse.",
    ),
    (
        re.compile(r"peligroso|riesgoso|sobre todo peligroso", re.IGNORECASE),
        "Un hallazgo catalogado como sospechoso no significa que sea peligroso de inmediato, pero sí requiere atención médica pronta para descartar o confirmar cualquier condición.",
    ),
    (
        re.compile(r"test|analisis|análisis", re.IGNORECASE),
        "El análisis de EcoScan revisa patrones visuales en imágenes y determina si coinciden con categorías benignas o malignas basadas en datos de entrenamiento. No es un diagnóstico médico, solo una herramienta informativa.",
    ),
    (
        re.compile(r"funcionas|cómo funcionas|funciona", re.IGNORECASE),
        "Funciono analizando patrones en base a modelos de inteligencia artificial entrenados con datos médicos. Mi función es apoyar, explicar resultados y recomendar acciones responsables.",
    ),
    (
        re.compile(r"modelo|arquitectura", re.IGNORECASE),
        "El modelo utilizado analiza características visuales en imágenes. Genera una predicción basada en similitud con patrones aprendidos durante su entrenamiento. Esto solo es una orientación y no sustituye una evaluación profesional.",
    ),
    (
        re.compile(r"confianza|accuracy|exactitud", re.IGNORECASE),
        "La confianza indica qué tan segura está la IA del patrón detectado. No representa un diagnóstico ni un porcentaje de cáncer. Solo mide la certeza técnica del análisis matemático.",
    ),
    (
        re.compile(r"estoy bien|está bien|más información|ayuda", re.IGNORECASE),
        "Si el resultado fue benigno, es una señal tranquila, pero lo ideal es llevarlo a un especialista para confirmarlo. Si fue maligno, la atención temprana es la clave.",
    ),
    (
        re.compile(r"ansioso|ansiosa|preocupado|nervioso", re.IGNORECASE),
        "Es normal sentirse así. Busca apoyo emocional y no te quedes con la incertidumbre. Consulta a un profesional para obtener respuestas claras y precisas.",
    ),
    (
        re.compile(r"importancia", re.IGNORECASE),
        "La importancia de este análisis es orientar, educar y promover la prevencion. La deteccion temprana siempre es la mejor estrategia.",
    ),
    (
        re.compile(r"benigno", re.IGNORECASE),
        "Un resultado benigno significa que el patrón detectado no muestra señales compatibles con cáncer de mama. Normalmente se trata de alteraciones que no representan riesgo grave, como quistes simples o masas no peligrosas. Sin embargo, aunque el hallazgo es tranquilizador, siempre es importante que consultes con un médico especialista para confirmar el diagnóstico con métodos clínicos y estudios adicionales si fuera necesario",
    ),
    (
        re.compile(r"maligno", re.IGNORECASE),
        "Un resultado maligno indica que el patrón analizado tiene características asociadas a cáncer de mama. Esto no es un diagnóstico definitivo, pero sí una señal importante para acudir cuanto antes a un médico especialista. El especialista podrá realizar estudios como mamografías, ultrasonidos o biopsias, que confirman el diagnóstico y permiten iniciar un tratamiento adecuado lo más temprano posible.",
    ),
]

FALLBACK = "No entendí muy bien, ¿podrías explicarlo un poco más?"


def responder(texto: str) -> str:
    """Retorna una respuesta al input ``texto`` usando reglas tolerantes.

    Solo una burbuja y una caja de chat (ver UI/chat_widget.py).
    """
    if not texto or not str(texto).strip():
        return FALLBACK
    t = str(texto).lower().strip()
    for pattern, reply in REGISTROS_ECO:
        if pattern.search(t):
            return reply
    return FALLBACK


__all__ = ["responder"]
