"""Asistente educativo con RAG y citas.

Sustituye el antiguo chat de reglas con expresiones regulares por un flujo
basado en recuperación local de documentos. Si ``ANTHROPIC_API_KEY`` y
``ANTHROPIC_MODEL`` están configurados, usa Claude; si no, responde en modo
extractivo con las fuentes citadas. Los guardrails de seguridad se aplican
siempre antes de cualquier respuesta.
"""

from __future__ import annotations

import streamlit as st

from ..rag.chat import llm_available, stream_answer
from ..rag.guardrails import DISCLAIMER

_SUGGESTIONS = [
    ("¿Qué es el autoexamen?", "¿Qué es el autoexamen y cómo se hace?"),
    ("Factores de riesgo", "¿Cuáles son los factores de riesgo del cáncer de mama?"),
    (
        "Interpretar un resultado",
        "¿Cómo debo interpretar un resultado no concluyente?",
    ),
    ("Síntomas de alarma", "¿Qué cambios en la mama merecen una consulta?"),
]


def init_chat_state() -> None:
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []


def _serialize_sources(sources) -> list[dict]:
    return [
        {
            "title": source.title,
            "doc_id": source.doc_id,
            "snippet": source.snippet,
            "score": source.score,
        }
        for source in sources
    ]


def _render_sources(sources: list[dict]) -> None:
    if not sources:
        return
    with st.expander(f"Fuentes ({len(sources)})", expanded=False):
        for index, source in enumerate(sources, start=1):
            st.markdown(f"**[{index}] {source['title']}**")
            st.caption(source["snippet"])
            st.caption(
                f"Documento: `{source['doc_id']}` · "
                f"relevancia: {float(source['score']):.3f}"
            )


def _last_result_context() -> str | None:
    result = st.session_state.get("scan_results")
    if not result:
        return None
    status = result.get("status")
    if status == "no_es_ecografia_mamaria":
        return (
            "Último análisis de la sesión: imagen no válida, sin clase ni porcentaje."
        )
    if status == "valida_no_concluyente":
        return "Último análisis de la sesión: no concluyente, sin clase forzada."
    if result.get("result"):
        confidence = result.get("confidence")
        confidence_text = (
            f" ({confidence}% de confianza calibrada)" if confidence else ""
        )
        return f"Último análisis de la sesión: {result['result']}{confidence_text}."
    return None


def _render_header() -> None:
    st.subheader("Asistente educativo")
    st.caption(
        "Pregunta sobre prevención, síntomas, estudios o cómo interpretar un "
        "resultado. Las respuestas se basan en documentos locales y citan sus "
        "fuentes. No es un diagnóstico."
    )
    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        if llm_available():
            st.badge(
                "Claude conectado",
                icon=":material/smart_toy:",
                color="green",
            )
        else:
            st.badge(
                "Recuperación local con citas",
                icon=":material/menu_book:",
                color="gray",
            )
    with c2:
        st.badge("No diagnostica", icon=":material/block:", color="red")
    with c3:
        st.badge(
            "No receta medicamentos",
            icon=":material/medication:",
            color="orange",
        )

    context = _last_result_context()
    if context:
        st.info(context, icon=":material/history:")


def _answer_prompt(prompt: str, history: list[dict[str, str]]) -> None:
    st.session_state.chat_messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    captured: dict[str, list[dict]] = {}

    def on_sources(sources) -> None:
        captured["sources"] = _serialize_sources(sources)

    with st.chat_message("assistant"):
        text = st.write_stream(
            stream_answer(
                prompt,
                history=history,
                last_result=st.session_state.get("scan_results"),
                on_sources=on_sources,
            )
        )
        sources = captured.get("sources", [])
        _render_sources(sources)

    st.session_state.chat_messages.append(
        {
            "role": "assistant",
            "content": text if isinstance(text, str) else str(text),
            "sources": sources,
        }
    )


def _clear_chat() -> None:
    st.session_state.chat_messages = []


def render_widget() -> None:
    """Pinta el asistente completo dentro de la pestaña correspondiente."""
    init_chat_state()
    _render_header()

    # ``st.chat_input`` se ancla al pie del contenedor aunque se declare antes
    # del historial. Así el historial queda arriba y el campo de escritura abajo.
    prompt = st.chat_input(
        "Escribe tu pregunta...",
        key="chat_input",
    )

    if prompt is None and not st.session_state.chat_messages:
        st.markdown("#### Prueba una pregunta")
        columns = st.columns(2)
        for index, (label, suggestion) in enumerate(_SUGGESTIONS):
            with columns[index % 2]:
                if st.button(
                    label,
                    key=f"chat_suggestion_{index}",
                    width="stretch",
                    icon=":material/lightbulb:",
                ):
                    prompt = suggestion

    for message in st.session_state.chat_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message["role"] == "assistant" and message.get("sources"):
                _render_sources(message["sources"])

    if prompt:
        history = [
            {"role": message["role"], "content": message["content"]}
            for message in st.session_state.chat_messages
        ]
        _answer_prompt(prompt, history)

    if st.session_state.chat_messages:
        st.divider()
        st.button(
            "Limpiar conversación",
            icon=":material/delete_sweep:",
            key="btn_clear_chat",
            on_click=_clear_chat,
        )
        st.caption(DISCLAIMER)


__all__ = ["init_chat_state", "render_widget"]
