"""Parsing and flagging of single lab values (plan sections 8.3 and 8.4).

Pure functions, no DB. Values stay Decimal so "7.2" never becomes 7.199999.
"""
import re
from decimal import Decimal

_NUM = r"\d+(?:\.\d+)?"
_VALUE_RE = re.compile(rf"^\s*(?P<qual>[<>]=?)?\s*(?P<num>{_NUM})\s*$")
_RANGE_BETWEEN_RE = re.compile(rf"^\s*(?P<low>{_NUM})\s*[-–]\s*(?P<high>{_NUM})\s*$")
_RANGE_LIMIT_RE = re.compile(rf"^\s*(?P<op>[<>])=?\s*(?P<num>{_NUM})\s*$")

# Lowercased spelling -> canonical spelling. Unknown units pass through unchanged.
_UNIT_SPELLINGS = {
    "uiu/ml": "µIU/mL",
    "ulu/ml": "µIU/mL",  # OCR reads capital I as l
    "µiu/ml": "µIU/mL",
    "μiu/ml": "µIU/mL",
    "microiu/ml": "µIU/mL",
    "miu/l": "µIU/mL",
    "mg/dl": "mg/dL",
    "gm/dl": "g/dL",
    "g/dl": "g/dL",
    "g/l": "g/L",
    "umol/l": "µmol/L",
    "µmol/l": "µmol/L",
    "μmol/l": "µmol/L",
    "mmol/l": "mmol/L",
    "nmol/l": "nmol/L",
    "pmol/l": "pmol/L",
    "ng/ml": "ng/mL",
    "ng/dl": "ng/dL",
    "pg/ml": "pg/mL",
    "u/l": "U/L",
    "iu/l": "U/L",
    "mmol/mol": "mmol/mol",
}


def parse_value(raw: str) -> tuple[Decimal | None, str | None]:
    """'7.2' -> (7.2, None); '<0.5' -> (0.5, '<'); 'Positive' -> (None, None)."""
    m = _VALUE_RE.match(raw.replace(",", ""))
    if not m:
        return None, None
    return Decimal(m["num"]), m["qual"]


def parse_range(raw: str | None) -> tuple[Decimal | None, Decimal | None]:
    """'4.0 - 5.6' -> (4.0, 5.6); '< 200' -> (None, 200); '> 40' -> (40, None)."""
    if not raw:
        return None, None
    if m := _RANGE_BETWEEN_RE.match(raw):
        return Decimal(m["low"]), Decimal(m["high"])
    if m := _RANGE_LIMIT_RE.match(raw):
        n = Decimal(m["num"])
        return (None, n) if m["op"] == "<" else (n, None)
    return None, None


def normalize_unit(raw: str | None) -> str | None:
    if raw is None:
        return None
    unit = raw.strip()
    return _UNIT_SPELLINGS.get(unit.lower(), unit)


def convert(value: Decimal, multiplier: Decimal, offset: Decimal = Decimal(0)) -> Decimal:
    return value * multiplier + offset


def compute_flag(
    value: Decimal | None,
    low: Decimal | None,
    high: Decimal | None,
    qualifier: str | None = None,
) -> str:
    """Flag using the range printed on the report. Never invents a range."""
    if value is None:
        return "non_numeric"
    if low is None and high is None:
        return "no_range"
    # "<0.5" is at most 0.5, so it can't be high if 0.5 isn't; same logic for ">".
    if low is not None and value < low and qualifier not in (">", ">="):
        return "low"
    if high is not None and value > high and qualifier not in ("<", "<="):
        return "high"
    return "normal"
