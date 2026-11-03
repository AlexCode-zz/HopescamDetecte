"""Recuperación local tipo TF-IDF, sin dependencias externas.

Para ~20 fragmentos es suficiente y determinista. Si el corpus crece, se puede
sustituir por embeddings multilingües + FAISS/ChromaDB manteniendo la interfaz
``Retriever.search``.
"""

from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from ..config import RAG_KNOWLEDGE_DIR, RAG_MIN_SCORE, RAG_TOP_K
from .chunking import Chunk, load_chunks

_STOPWORDS = {
    "a",
    "al",
    "algo",
    "aunque",
    "de",
    "del",
    "el",
    "ella",
    "ellas",
    "ellos",
    "en",
    "es",
    "esa",
    "ese",
    "eso",
    "esta",
    "este",
    "esto",
    "fue",
    "ha",
    "han",
    "hay",
    "la",
    "las",
    "le",
    "les",
    "lo",
    "los",
    "más",
    "me",
    "mi",
    "mis",
    "mucho",
    "muy",
    "no",
    "nos",
    "o",
    "otra",
    "otro",
    "para",
    "pero",
    "por",
    "puede",
    "que",
    "qué",
    "se",
    "ser",
    "si",
    "sí",
    "sin",
    "sobre",
    "son",
    "su",
    "sus",
    "también",
    "te",
    "tiene",
    "todo",
    "tu",
    "tus",
    "un",
    "una",
    "uno",
    "y",
    "ya",
    "yo",
    "con",
    "como",
    "cómo",
    "cuando",
    "cuándo",
    "donde",
    "dónde",
    "porque",
    "cual",
    "cuál",
    "cuales",
    "cuáles",
}


def normalize(text: str) -> str:
    """Minúsculas y sin tildes, para comparar de forma robusta."""
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def tokenize(text: str) -> list[str]:
    words = re.findall(r"[a-z0-9]{3,}", normalize(text))
    return [word for word in words if word not in _STOPWORDS]


@dataclass(frozen=True)
class Retrieved:
    chunk: Chunk
    score: float


class Retriever:
    """Índice TF-IDF en memoria con similitud coseno."""

    def __init__(self, chunks: list[Chunk]):
        self.chunks = chunks
        self._documents = [tokenize(chunk.text) for chunk in chunks]
        document_frequency: Counter[str] = Counter()
        for tokens in self._documents:
            document_frequency.update(set(tokens))

        total = max(len(chunks), 1)
        self._idf = {
            term: math.log((total + 1) / (frequency + 1)) + 1.0
            for term, frequency in document_frequency.items()
        }
        self._vectors = [self._vectorize(tokens) for tokens in self._documents]

    def _vectorize(self, tokens: list[str]) -> dict[str, float]:
        counts = Counter(tokens)
        vector = {
            term: count * self._idf.get(term, 1.0)
            for term, count in counts.items()
            if term in self._idf
        }
        norm = math.sqrt(sum(value * value for value in vector.values()))
        if norm:
            vector = {term: value / norm for term, value in vector.items()}
        return vector

    def search(self, query: str, k: int = RAG_TOP_K) -> list[Retrieved]:
        query_vector = self._vectorize(tokenize(query))
        if not query_vector:
            return []
        scored: list[tuple[int, float, Retrieved]] = []
        for chunk, vector in zip(self.chunks, self._vectors):
            shared = [term for term in query_vector if term in vector]
            if not shared:
                continue
            score = sum(
                value * vector.get(term, 0.0) for term, value in query_vector.items()
            )
            scored.append((len(shared), score, Retrieved(chunk=chunk, score=score)))
        # Primero los fragmentos que cubren más términos de la pregunta; ante
        # empate, la similitud TF-IDF. En un corpus pequeño esto evita que un
        # fragmento corto con una sola palabra repetida gane a la sección que
        # realmente responde la pregunta.
        scored.sort(key=lambda item: (-item[0], -item[1]))
        return [item[2] for item in scored[:k]]


def build_retriever(directory: str | Path | None = None) -> Retriever:
    """Construye un índice a partir de un directorio de conocimiento."""
    return Retriever(load_chunks(directory or RAG_KNOWLEDGE_DIR))


@lru_cache(maxsize=2)
def get_default_retriever(directory: str | None = None) -> Retriever:
    """Índice cacheado del corpus por defecto (se reinicia al reiniciar la app)."""
    return build_retriever(directory)


def is_relevant(results: list[Retrieved], minimum: float = RAG_MIN_SCORE) -> bool:
    return bool(results) and results[0].score >= minimum


__all__ = [
    "Retrieved",
    "Retriever",
    "build_retriever",
    "get_default_retriever",
    "is_relevant",
    "normalize",
    "tokenize",
]
