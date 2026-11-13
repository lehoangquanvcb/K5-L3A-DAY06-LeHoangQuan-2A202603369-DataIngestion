"""Compare fixed windows with paragraph-aware chunks on each OCR page."""
import uuid

from .ingestion import evidence_text
from .models import Chunk, DocumentPage


def make_chunks(page: DocumentPage, texts: list[str], strategy: str) -> list[Chunk]:
    return [
        Chunk(str(uuid.uuid5(uuid.NAMESPACE_URL, f"{page.document_id}/{page.page}/{strategy}/{i}")),
              page.document_id, page.source, page.page, text, page.metadata.copy())
        for i, text in enumerate(texts)
    ]


def windows(text: str, size: int, overlap: int) -> list[str]:
    parts = []
    for start in range(0, len(text), size - overlap):
        parts.append(text[start:start + size].strip())
        if start + size >= len(text):
            break
    return parts


def fixed_size(page: DocumentPage, size: int, overlap: int) -> list[Chunk]:
    return make_chunks(page, windows(evidence_text(page.text), size, overlap), "A")


def by_paragraph(page: DocumentPage, max_size: int) -> list[Chunk]:
    parts = []
    current = ""
    for paragraph in page.text.split("\n\n"):
        combined = f"{current}\n\n{paragraph}" if current else paragraph
        if len(combined) <= max_size:
            current = combined
            continue
        if current:
            parts.append(current)
        if len(paragraph) <= max_size:
            current = paragraph
        else:
            parts.extend(windows(paragraph, max_size, 80))
            current = ""
    if current:
        parts.append(current)
    return make_chunks(page, parts, "B")
