"""Rule-based document facts (plan 7.2): report date, lab chain, document type. Cheap and explainable."""
import re
from datetime import date

_MONTHS = {m: i + 1 for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])}
_DATE = (
    r"(?P<iso>\d{4}-\d{1,2}-\d{1,2})"
    r"|(?P<dmy>\d{1,2}[/.\-]\d{1,2}[/.\-]\d{2,4})"
    r"|(?P<dmony>\d{1,2}[\s\-/]*[a-z]{3,9}[\s\-/,]*\d{2,4})"
)
# Indian reports: collection date is the one that matters for a trend; then reported, then registered.
# Discharge summaries: the discharge date, else the admission date.
_LABELS_BY_PRIORITY = [r"collect\w*", r"report\w*", r"regist\w*|reg\.?\s*date", r"discharg\w*", r"admi(?:t|ss)\w*"]

_LAB_CHAINS = {
    "lal pathlabs": "Dr Lal PathLabs",
    "thyrocare": "Thyrocare",
    "srl diagnostics": "SRL Diagnostics",
    "agilus": "Agilus Diagnostics",
    "metropolis": "Metropolis",
    "redcliffe": "Redcliffe Labs",
    "apollo diagnostics": "Apollo Diagnostics",
    "healthians": "Healthians",
    "vijaya diagnostic": "Vijaya Diagnostic",
    "neuberg": "Neuberg Diagnostics",
}

_LAB_KEYWORDS = ["reference range", "ref. range", "reference interval", "biological ref", "bio. ref",
                 "test name", "units", "sample collected", "nabl"]
_MED_LINE_RE = re.compile(r"\b(?:tab|cap|syp|syr|inj)\.?\s+[a-z]", re.IGNORECASE)
_RX_MARKERS = [r"\brx\b", r"\breg\.?\s*no", r"\b\d-\d-\d\b", r"\b(?:od|bd|bid|tds|tid|qid|hs|sos)\b"]


def find_report_date(text: str) -> date | None:
    for label in _LABELS_BY_PRIORITY:
        for m in re.finditer(rf"(?:{label})[^\d\n]{{0,25}}(?:{_DATE})", text, re.IGNORECASE):
            if d := _parse_date(m):
                return d
    return None


def _parse_date(m: re.Match) -> date | None:
    try:
        if m["iso"]:
            y, mo, d = map(int, m["iso"].split("-"))
        elif m["dmy"]:
            d, mo, y = map(int, re.split(r"[/.\-]", m["dmy"]))
        else:
            parts = re.match(r"(\d{1,2})[\s\-/]*([a-z]+)[\s\-/,]*(\d{2,4})", m["dmony"], re.IGNORECASE)
            d, mo, y = int(parts[1]), _MONTHS.get(parts[2][:3].lower()), int(parts[3])
            if mo is None:
                return None
        if y < 100:
            y += 2000
        return date(y, mo, d)
    except ValueError:
        return None  # e.g. 31/02/2026


def find_lab_name(text: str) -> str | None:
    lower = text.lower()
    return next((name for key, name in _LAB_CHAINS.items() if key in lower), None)


def classify_document(text: str, lab_row_count: int) -> str:
    lower = text.lower()
    if lab_row_count >= 3 and any(k in lower for k in _LAB_KEYWORDS):
        return "lab_report"
    # Before prescriptions: discharge summaries list medicines too.
    if "discharge summary" in lower or ("discharge" in lower and "diagnosis" in lower):
        return "discharge"
    if _MED_LINE_RE.search(text) and any(re.search(p, lower) for p in _RX_MARKERS):
        return "prescription"
    return "other"
