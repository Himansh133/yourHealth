"""Question router, rules stage (plan 10.3).

Fast and explainable. When the rules can't decide, labels is empty and the LLM classifier takes over.
"""
import re
from dataclasses import dataclass, field

from app.services.labs.dictionary import LabDictionary, LabTest, normalize_name

TREATMENT = re.compile(
    r"\b(?:should i (?:take|stop|start)|stop taking|which (?:medicine|tablet|drug)|what (?:medicine|tablet) should"
    r"|kaunsi dawai|kaun si dawai|dawai band|dose badha|dose kam|change (?:the |my )?dose)\b"
)
TREND_WORDS = {"trend", "improving", "improved", "better", "worse", "worsening", "change", "changed", "over",
               "badha", "badhi", "ghata", "ghati", "down", "up", "history"}
# Chat only, not used for parsing reports: a row printed as "Sugar" could be urine sugar.
EVERYDAY_TERMS = {
    "sugar": ["4548-4", "1558-6"], "shugar": ["4548-4", "1558-6"], "glucose": ["4548-4", "1558-6"],
    "diabetes": ["4548-4", "1558-6"], "thyroid": ["3016-3", "3024-7"], "kidney": ["2160-0", "3084-1"],
    "liver": ["1742-6", "1920-8"], "lipid": ["2093-3", "13457-7", "2085-9", "2571-8"],
}
VALUE_WORDS = {"last", "latest", "recent", "current", "value", "result", "level", "kitna", "kitni"}


@dataclass(frozen=True)
class Route:
    labels: list[str]  # value | trend | document | medicine | medicine_lab | treatment | out_of_scope
    tests: list[LabTest] = field(default_factory=list)
    medicines: list[str] = field(default_factory=list)


def route(question: str, d: LabDictionary, medicine_names: set[str]) -> Route:
    """medicine_names: lowercase brand and generic names to look for."""
    lower = question.lower()
    words = set(re.findall(r"[a-z0-9]+", lower))
    tests = _find_tests(question, d)
    meds = sorted(m for m in medicine_names if re.search(rf"\b{re.escape(m)}\b", lower))

    if TREATMENT.search(lower):
        return Route(["treatment"], tests, meds)
    if meds:
        return Route(["medicine_lab" if tests else "medicine"], tests, meds)
    if tests and words & TREND_WORDS:
        return Route(["trend"], tests)
    if tests and words & (VALUE_WORDS | EVERYDAY_TERMS.keys()):
        return Route(["value"], tests)
    return Route([], tests)


def _find_tests(question: str, d: LabDictionary) -> list[LabTest]:
    """The longest test alias in the question, or else the tests an everyday word stands for."""
    text = " " + " ".join(p for p in normalize_name(question) if p) + " "
    found = [alias for alias in d.aliases if f" {alias} " in text]
    if found:
        return [d.aliases[max(found, key=len)]]
    words = text.split()
    return [d.tests[code] for term, codes in EVERYDAY_TERMS.items() if term in words for code in codes]
