"""Fragmentación de documentos Markdown para el RAG."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Chunk:
    """Un fragmento recuperable de un documento."""

    doc_id: str
    title: str
    source: str
    text: str
    chunk_id: int

    @property
    def citation(self) -> str:
        return f"{self.title} — {self.source}"


def _clean(text: str) -> str:
    text = re.sub(r"\r\n?", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def _split_long(text: str, max_chars: int, overlap: int) -> list[str]:
    """Divide un bloque largo respetando párrafos y frases."""
    if len(text) <= max_chars:
        return [text]

    units = re.split(r"(?<=[.!?])\s+|\n{2,}", text)
    chunks: list[str] = []
    current = ""
    for unit in units:
        unit = unit.strip()
        if not unit:
            continue
        candidate = f"{current} {unit}".strip() if current else unit
        if len(candidate) <= max_chars:
            current = candidate
            continue
        if current:
            chunks.append(current)
            tail = current[-overlap:] if overlap else ""
            current = f"{tail} {unit}".strip()
        else:
            # Una sola frase gigante: corte por caracteres.
            start = 0
            while start < len(unit):
                chunks.append(unit[start : start + max_chars])
                start += max_chars - overlap
            current = ""
    if current:
        chunks.append(current)
    return [chunk for chunk in chunks if chunk]


def split_markdown(
    text: str,
    *,
    doc_id: str,
    title: str,
    source: str,
    max_chars: int = 900,
    overlap: int = 120,
) -> list[Chunk]:
    """Divide un documento por secciones ``##`` y por tamaño máximo."""
    text = _clean(text)
    # Elimina el título y la nota de ejemplo del cuerpo recuperable.
    lines = text.splitlines()
    body_lines = [
        line
        for line in lines
        if not line.startswith("# ")
        and not line.strip().startswith("> **Documento de ejemplo")
    ]
    body = "\n".join(body_lines).strip()

    sections = re.split(r"\n(?=##\s+)", body)
    chunks: list[Chunk] = []
    index = 0
    for section in sections:
        section = section.strip()
        if not section:
            continue
        for piece in _split_long(section, max_chars, overlap):
            chunk_text = f"{title}\n\n{piece}".strip()
            chunks.append(
                Chunk(
                    doc_id=doc_id,
                    title=title,
                    source=source,
                    text=chunk_text,
                    chunk_id=index,
                )
            )
            index += 1
    return chunks


def load_chunks(directory: str | Path) -> list[Chunk]:
    """Carga todos los ``.md`` de un directorio como fragmentos."""
    path = Path(directory)
    if not path.exists():
        return []
    chunks: list[Chunk] = []
    for file in sorted(path.glob("*.md")):
        raw = file.read_text(encoding="utf-8", errors="replace")
        title_match = re.search(r"^#\s+(.+)$", raw, re.MULTILINE)
        title = title_match.group(1).strip() if title_match else file.stem
        source_match = re.search(
            r"^>\s*\*\*Documento de ejemplo\.\*\*\s*(.+)$", raw, re.MULTILINE
        )
        source = (
            source_match.group(1).strip()
            if source_match
            else "Documento local de HopeScan"
        )
        chunks.extend(
            split_markdown(
                raw,
                doc_id=file.stem,
                title=title,
                source=source,
            )
        )
    return chunks


__all__ = ["Chunk", "load_chunks", "split_markdown"]
