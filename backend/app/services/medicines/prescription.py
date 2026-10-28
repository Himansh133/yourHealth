"""Find medicine lines in a printed prescription (plan 9.1). Nothing is saved until the user confirms."""
import re
from dataclasses import dataclass

_FORM_RE = re.compile(
    r"^(?P<form>tab|cap|syp|syr|inj|oint|drops|tablet|capsule|syrup)\.?\s+(?P<rest>.+)$", re.IGNORECASE
)
_ABBREVIATIONS = {"tab", "cap", "syp", "syr", "inj", "oint", "drops"}
_FREQ_RE = re.compile(r"(?<![\w-])(\d-\d-\d(?:-\d)?|OD|BD|BID|TDS|TID|QID|HS|SOS)(?![\w-])", re.IGNORECASE)
_DURATION_RE = re.compile(r"\bx\s?(\d+)\s?(days?|d|weeks?|wks?|months?)\b", re.IGNORECASE)
_CODES = {"BID": "BD", "TID": "TDS"}
_DOSES_PER_DAY = {1: "OD", 2: "BD", 3: "TDS", 4: "QID"}


@dataclass(frozen=True)
class RxLine:
    form: str  # 'tab' | 'cap' | ...
    brand_text: str  # what to match against brands, e.g. "Glycomet 500"
    frequency_code: str | None  # OD | BD | TDS | QID | HS | SOS
    frequency_raw: str | None  # as printed, e.g. "1-0-1"
    duration: str | None  # e.g. "30 days"


def parse_prescription_line(line: str) -> RxLine | None:
    line = re.sub(r"^\s*\d+[.)]\s*", "", line.strip())
    m = _FORM_RE.match(line)
    if not m:
        return None
    form, rest = m["form"].lower(), m["rest"]
    # "Tablet should be taken after food" is advice, not a medicine: full words need a Capitalised name next.
    if form not in _ABBREVIATIONS and not rest[0].isupper():
        return None
    form = {"tablet": "tab", "capsule": "cap", "syrup": "syp", "syr": "syp"}.get(form, form)

    duration_m = _DURATION_RE.search(rest)
    duration = f"{duration_m[1]} {duration_m[2]}" if duration_m else None
    freq_m = _FREQ_RE.search(rest)
    cut = min(x.start() for x in (freq_m, duration_m) if x) if (freq_m or duration_m) else len(rest)
    brand_text = rest[:cut].strip(" ,.-")
    if not brand_text:
        return None

    raw = freq_m[1].upper() if freq_m else None
    return RxLine(form, brand_text, _frequency_code(raw), raw, duration)


def _frequency_code(raw: str | None) -> str | None:
    if raw is None:
        return None
    if "-" in raw:
        doses = sum(1 for part in raw.split("-") if part != "0")
        return _DOSES_PER_DAY.get(doses)
    return _CODES.get(raw, raw)
