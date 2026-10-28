"""Find lab result rows in page text (plan 7.3).

One parser for both text-layer words and OCR boxes: group boxes into lines, then for each line
try split points from the left until the right side reads as "value [flag] [unit] [range] [unit]".
This survives lost column gaps (text layer) and glued cells (OCR "7.2%").
"""
import re
from dataclasses import dataclass

from app.services.extraction.ocr import group_rows
from app.services.labs.values import normalize_unit

_NUM = r"\d+(?:\.\d+)?"
_UNIT = r"(?:10\^\d+/\S+|[^\s\d<>\-–][^\s]*)"
_RANGE = rf"(?:{_NUM}\s*[-–]\s*{_NUM}|[<>]=?\s*{_NUM}|up\s*to\s*{_NUM})"
_TAIL_RE = re.compile(
    rf"""^(?P<value>(?:[<>]=?)?\s*{_NUM})
    (?:\s*(?P<flag>H|L|High|Low)(?=\s|$))?
    (?:\s*(?P<unit>{_UNIT}))?
    (?:\s+(?P<range>{_RANGE}))?
    (?:\s+(?P<unit2>{_UNIT}))?
    \s*$""",
    re.VERBOSE | re.IGNORECASE,
)

# Units we accept without a printed range. Anything else needs a range to count as a result,
# which keeps header lines like "Age 58 Years" out.
KNOWN_UNITS = {
    u.lower()
    for u in [
        "%", "mg/dL", "g/dL", "g/L", "mg/L", "µg/dL", "ng/dL", "ng/mL", "pg/mL", "µIU/mL", "IU/mL", "U/L",
        "mmol/L", "µmol/L", "nmol/L", "pmol/L", "mmol/mol", "mEq/L", "fL", "pg", "mm/hr", "cells/cumm",
        "/cumm", "lakhs/cumm", "mill/cumm", "million/cumm", "10^3/µL", "10^6/µL",
    ]
}


@dataclass(frozen=True)
class RawRow:
    raw_name: str
    raw_value: str  # as printed, including any "<" / ">"
    raw_unit: str | None
    raw_range: str | None
    printed_flag: str | None  # 'H' | 'L' if the report printed one
    bbox: dict | None = None  # {x0, y0, x1, y1} on the page, for highlighting


def parse_line(line: str) -> RawRow | None:
    tokens = line.split()
    for i in range(1, len(tokens)):
        name = " ".join(tokens[:i])
        if not name[0].isalpha():
            return None  # plan 7.3: a test name starts with a letter
        m = _TAIL_RE.match(" ".join(tokens[i:]))
        if not m:
            continue
        unit = m["unit"] or m["unit2"]
        if m["unit"] and m["unit2"]:
            continue
        if m["range"] is None and (unit is None or normalize_unit(unit).lower() not in KNOWN_UNITS):
            continue
        flag = m["flag"][0].upper() if m["flag"] else None
        return RawRow(name, m["value"].replace(" ", ""), unit, m["range"], flag)
    return None


def parse_words(words: list[dict]) -> list[RawRow]:
    rows = []
    for line_words in group_rows(words):
        parsed = parse_line(" ".join(w["text"] for w in line_words))
        if parsed:
            bbox = {
                "x0": min(w["x0"] for w in line_words), "y0": min(w["y0"] for w in line_words),
                "x1": max(w["x1"] for w in line_words), "y1": max(w["y1"] for w in line_words),
            }
            rows.append(RawRow(**{**parsed.__dict__, "bbox": bbox}))
    return rows
