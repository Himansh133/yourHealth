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
VALUE_WORDS = {"last", "latest", "recent", "current", "value", "result", "level", "kitna", "kitni"}


@dataclass(frozen=True)
class Route:
    labels: list[str]  # value | trend | document | medicine | medicine_lab | treatment | out_of_scope
    test: LabTest | None = None
    medicines: list[str] = field(default_factory=list)


def route(question: str, d: LabDictionary, medicine_names: set[str]) -> Route:
    """medicine_names: lowercase brand and ingredient names known for this profile."""
    lower = question.lower()
    words = set(re.findall(r"[a-z0-9]+", lower))
    test = _find_test(question, d)
    meds = sorted(m for m in medicine_names if re.search(rf"\b{re.escape(m)}\b", lower))

    if TREATMENT.search(lower):
        return Route(["treatment"], test, meds)
    if meds:
        return Route(["medicine_lab" if test else "medicine"], test, meds)
    if test and words & TREND_WORDS:
        return Route(["trend"], test)
    if test and words & VALUE_WORDS:
        return Route(["value"], test)
    return Route([], test)


def _find_test(question: str, d: LabDictionary) -> LabTest | None:
    """Longest alias that appears as whole words in the question."""
    text = " " + " ".join(p for p in normalize_name(question) if p) + " "
    found = [alias for alias in d.aliases if f" {alias} " in text]
    return d.aliases[max(found, key=len)] if found else None
