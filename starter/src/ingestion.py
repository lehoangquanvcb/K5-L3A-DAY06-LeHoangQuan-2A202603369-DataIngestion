"""Load selected VIC pages from the local OCR exports."""
import hashlib
import json
import re
import unicodedata
from pathlib import Path

from .models import DocumentPage


def evidence_text(text: str) -> str:
    return " ".join(unicodedata.normalize("NFC", text).split())


def normalize_text(text: str) -> str:
    paragraphs = re.split(r"\n\s*\n", text)
    return "\n\n".join(clean for part in paragraphs if (clean := evidence_text(part)))


def load_ocr(directory: Path, manifest_path: Path) -> list[DocumentPage]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    pages = []
    for entry in manifest["page_selection"]["pages"]:
        if not entry["include"]:
            continue
        number = entry["pdf_page"]
        path = directory / f"page-{number:03}.txt"
        if not path.is_file():
            raise ValueError(f"Missing OCR export: {path}")
        text = normalize_text(path.read_text(encoding="utf-8-sig"))
        if len(evidence_text(text)) != entry["normalized_ocr_characters"]:
            raise ValueError(f"OCR length differs from manifest: {path}")
        pages.append(DocumentPage(
            manifest["source_id"], manifest["source_path_or_url"], number, text,
            {"note_topic": entry["note_topic"], "section": entry["section"],
             "printed_page": number - 3},
        ))
    if len({page.page for page in pages}) < 30 or len({p.metadata["note_topic"] for p in pages}) < 2:
        raise ValueError("Expected at least 30 distinct pages and two note topics.")
    return pages


def corpus_digest(pages: list[DocumentPage]) -> str:
    return hashlib.sha256(json.dumps(
        [vars(page) for page in pages], ensure_ascii=False, sort_keys=True
    ).encode("utf-8")).hexdigest()
