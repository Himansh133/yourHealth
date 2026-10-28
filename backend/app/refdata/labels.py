"""Pure helpers for openFDA drug labels (plan 9.3, 9.4). The network fetch lives in fetch_openfda.py."""
import re

# warnings_and_cautions is the PLR section; older labels only have "warnings".
_FALLBACK = {"warnings_and_cautions": "warnings"}


def pick_label(results: list[dict]) -> dict | None:
    """Single-ingredient label; oral before other routes (people take these at home); prescription before
    OTC; newest first. Combination products are skipped: their text mixes effects of several molecules."""
    single = [r for r in results if len(r.get("openfda", {}).get("substance_name", [])) == 1]
    if not single:
        return None

    def rank(r):
        oral = "ORAL" in r["openfda"].get("route", [])
        rx = "HUMAN PRESCRIPTION DRUG" in r["openfda"].get("product_type", [])
        return (oral, rx, r.get("effective_time", ""))

    return max(single, key=rank)


def section_text(label: dict, section: str) -> str:
    paragraphs = label.get(section) or label.get(_FALLBACK.get(section, ""), [])
    return " ".join(paragraphs)


def first_sentence(text: str) -> str:
    text = re.sub(r"^\s*[\d.]*\s*INDICATIONS\s*(&|AND)\s*USAGE\s*", "", text, flags=re.IGNORECASE)
    m = re.match(r"(.+?[.!?])(\s|$)", text.strip())
    return m.group(1) if m else text.strip()


def verify_effect(label: dict, section: str, evidence: str) -> bool:
    """True if any '|'-separated evidence phrase appears in the cited section (case/space-insensitive)."""
    haystack = _squash(section_text(label, section))
    return any(_squash(phrase) in haystack for phrase in evidence.split("|"))


def _squash(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()
