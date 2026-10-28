"""OCR for scanned pages and photos, using RapidOCR (PaddleOCR models on ONNX Runtime)."""
import logging
from functools import lru_cache

from app.services.extraction.text_layer import PageText

logging.getLogger("RapidOCR").setLevel(logging.WARNING)


@lru_cache
def _engine():
    from rapidocr import RapidOCR  # heavy import; only the worker pays for it

    return RapidOCR()


def rapid_ocr(image: bytes, page_no: int) -> PageText:
    """Boxes are in image pixels. Lines come back top to bottom."""
    result = _engine()(image)
    if not result.txts:
        return PageText(page_no=page_no, method="rapidocr", text="", words=[], ocr_confidence=None)
    words = []
    for text, score, box in zip(result.txts, result.scores, result.boxes):
        xs, ys = [float(p[0]) for p in box], [float(p[1]) for p in box]
        words.append(
            {"text": text, "x0": round(min(xs), 1), "y0": round(min(ys), 1),
             "x1": round(max(xs), 1), "y1": round(max(ys), 1), "conf": round(float(score), 3)}
        )
    return PageText(
        page_no=page_no,
        method="rapidocr",
        text="\n".join("  ".join(w["text"] for w in row) for row in group_rows(words)),
        words=words,
        ocr_confidence=round(sum(result.scores) / len(result.scores), 3),
    )


def group_rows(boxes: list[dict]) -> list[list[dict]]:
    """Group boxes on the same visual line; left to right within a row.

    OCR splits one table row into several boxes when columns are far apart. Rows are joined
    with two spaces so the column gaps survive for the regex parser (plan 7.3, tier 2).
    """
    rows: list[list[dict]] = []
    for box in sorted(boxes, key=lambda b: (b["y0"] + b["y1"]) / 2):
        mid = (box["y0"] + box["y1"]) / 2
        if rows:
            last = rows[-1]
            last_mid = sum((b["y0"] + b["y1"]) / 2 for b in last) / len(last)
            half_height = (last[0]["y1"] - last[0]["y0"]) / 2
            if abs(mid - last_mid) <= half_height:
                last.append(box)
                continue
        rows.append([box])
    return [sorted(row, key=lambda b: b["x0"]) for row in rows]
