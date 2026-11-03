"""RAG educativo de HopeScan (recuperación local + LLM opcional)."""

from .chat import Answer, Source, answer, llm_available, stream_answer
from .guardrails import DISCLAIMER, GuardrailResult, check
from .retriever import (
    Retrieved,
    Retriever,
    build_retriever,
    get_default_retriever,
    is_relevant,
)

__all__ = [
    "DISCLAIMER",
    "Answer",
    "GuardrailResult",
    "Retrieved",
    "Retriever",
    "Source",
    "answer",
    "build_retriever",
    "check",
    "get_default_retriever",
    "is_relevant",
    "llm_available",
    "stream_answer",
]
