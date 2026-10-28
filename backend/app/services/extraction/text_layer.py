"""Text layer extraction for digital PDFs, and the per-page "is this scanned?" check (plan 7.2)."""
from dataclasses import dataclass, field

import pymupdf

MIN_WORDS = 20
MIN_READABLE_RATIO = 0.5


@dataclass
class PageText:
    page_no: int  # 1-based
    method: str  # 'text_layer' | OCR engine name
    text: str
    words: list[dict] = field(default_factory=list)  # [{text, x0, y0, x1, y1[, conf]}]
    ocr_confidence: float | None = None


def extract_text_layer(pdf_bytes: bytes) -> list[PageText]:
    pages = []
    with pymupdf.open(stream=pdf_bytes, filetype="pdf") as doc:
        for i, page in enumerate(doc):
            words = [
                {"text": w[4], "x0": round(w[0], 1), "y0": round(w[1], 1), "x1": round(w[2], 1), "y1": round(w[3], 1)}
                for w in page.get_text("words", sort=True)
            ]
            pages.append(PageText(page_no=i + 1, method="text_layer", text=page.get_text("text", sort=True), words=words))
    return pages


def needs_ocr(page: PageText) -> bool:
    """Decided per page, since some PDFs mix digital and scanned pages."""
    if len(page.words) < MIN_WORDS:
        return True
    chars = [c for c in page.text if not c.isspace()]
    readable = sum(_is_readable(c) for c in chars)
    return readable / len(chars) < MIN_READABLE_RATIO


def _is_readable(c: str) -> bool:
    # ASCII letters/digits or Devanagari. Broken font encodings tend to produce Latin-1 junk like "ï¿½".
    return (c.isascii() and c.isalnum()) or "\u0900" <= c <= "\u097f"
