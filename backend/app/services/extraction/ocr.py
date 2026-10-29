"""OCR for scanned pages and photos, using RapidOCR (PaddleOCR models on ONNX Runtime)."""
import logging
import math
import statistics
from functools import lru_cache

from app.services.extraction.text_layer import PageText

logging.getLogger("RapidOCR").setLevel(logging.WARNING)

MIN_BOX_WIDTH_FOR_TILT = 40  # px; short boxes give noisy angles


@lru_cache
def _engine():
    from rapidocr import RapidOCR  # heavy import; only the worker pays for it

    return RapidOCR()


def rapid_ocr(image: bytes, page_no: int) -> PageText:
    """Boxes are in image pixels. Lines come back top to bottom."""
    result = _engine()(image)
    if not result.txts:
        return PageText(page_no=page_no, method="rapidocr", text="", words=[], ocr_confidence=None)
    tilt = math.radians(estimate_tilt(result.boxes))
    words = []
    for text, score, box in zip(result.txts, result.scores, result.boxes):
        xs, ys = [float(p[0]) for p in box], [float(p[1]) for p in box]
        cx, cy = sum(xs) / 4, sum(ys) / 4
        words.append(
            {"text": text, "x0": round(min(xs), 1), "y0": round(min(ys), 1),
             "x1": round(max(xs), 1), "y1": round(max(ys), 1), "conf": round(float(score), 3),
             # height of the box centre once the page is turned level: what row grouping should compare
             "ym": round(cy * math.cos(tilt) - cx * math.sin(tilt), 1)}
        )
    return PageText(
        page_no=page_no,
        method="rapidocr",
        text="\n".join("  ".join(w["text"] for w in row) for row in group_rows(words)),
        words=words,
        ocr_confidence=round(sum(result.scores) / len(result.scores), 3),
    )


def estimate_tilt(boxes) -> float:
    """Page tilt in degrees: the median slope of the top edge of OCR boxes wide enough to measure it."""
    angles = [math.degrees(math.atan2(b[1][1] - b[0][1], b[1][0] - b[0][0]))
              for b in boxes if b[1][0] - b[0][0] > MIN_BOX_WIDTH_FOR_TILT]
    return statistics.median(angles) if angles else 0.0


def group_rows(boxes: list[dict]) -> list[list[dict]]:
    """Group boxes on the same visual line; left to right within a row.

    OCR splits one table row into several boxes when columns are far apart. Rows are joined
    with two spaces so the column gaps survive for the regex parser (plan 7.3, tier 2).
    """
    def mid(b: dict) -> float:  # OCR boxes carry a tilt-corrected height; text-layer words are level already
        return b.get("ym", (b["y0"] + b["y1"]) / 2)

    rows: list[list[dict]] = []
    for box in sorted(boxes, key=mid):
        if rows:
            last = rows[-1]
            last_mid = sum(mid(b) for b in last) / len(last)
            half_height = (last[0]["y1"] - last[0]["y0"]) / 2
            if abs(mid(box) - last_mid) <= half_height:
                last.append(box)
                continue
        rows.append([box])
    return [sorted(row, key=lambda b: b["x0"]) for row in rows]
