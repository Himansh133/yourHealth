"""Checks every LLM answer before it is shown (plan 10.8).

The number check is the main guard against made-up values: every number the model writes must appear in the
evidence it cites (or, for the summary and notes, somewhere in the evidence we sent).
"""
import re
from dataclasses import dataclass
from decimal import Decimal

from pydantic import BaseModel, ValidationError

# Digits right after a letter are part of a name (HbA1c, B12, T4), not a value; "850mg" is still a value.
NUMBER = re.compile(r"(?<![A-Za-z\d.])\d+(?:\.\d+)?")

# Advice or diagnosis the assistant must never give, in English and Hinglish.
BANNED = re.compile(
    r"stop taking|start taking|(?:increase|decrease|reduce|change|double) (?:the |your )?dose"
    r"|dawai band|dawa band|dose badha|dose kam"
    r"|दवा बंद|दवाई बंद|दवाइयाँ बंद|दवाएं बंद|लेना बंद|खुराक बढ़ा|खुराक कम|डोज़ बढ़ा|डोज बढ़ा|डोज़ कम|डोज कम"
    r"|you have (?:diabetes|cancer|hypothyroidism|hyperthyroidism|anaemia|anemia|kidney disease|liver disease)",
    re.IGNORECASE,
)
# A warning against changing a medicine ("do not stop or change the dose") is not advice. English only: Hindi
# negation comes after the verb, so Hindi phrases are always caught.
NEGATED = re.compile(r"\b(?:do not|don't|never|should not|shouldn't|must not|not to)\s+(?:\w+\s+){0,2}$", re.IGNORECASE)


def advice_phrase(text: str) -> str | None:
    """The first banned phrase in text that isn't a warning against it."""
    for m in BANNED.finditer(text):
        if not NEGATED.search(text[:m.start()]):
            return m.group(0)
    return None


@dataclass(frozen=True)
class Evidence:
    id: str  # E1, E2, ...
    text: str


class Claim(BaseModel):
    text: str
    evidence_ids: list[str]


class Answer(BaseModel):
    answerable: bool
    summary: str
    claims: list[Claim]
    missing_info: list[str]
    doctor_note: str


def _numbers(text: str) -> set[Decimal]:
    return {Decimal(n) for n in NUMBER.findall(text)}


def _unsupported(text: str, evidence_text: str) -> list[Decimal]:
    allowed = _numbers(evidence_text)
    return [n for n in map(Decimal, NUMBER.findall(text)) if n not in allowed]


def _without_names(text: str, names: list[str]) -> str:
    for name in names:
        text = re.sub(re.escape(name), " ", text, flags=re.IGNORECASE)
    return text


def validate_answer(raw: str, evidence: list[Evidence], names: list[str] = ()) -> tuple[Answer | None, list[str]]:
    """Returns the parsed answer and a list of errors; an empty list means it passed.
    names: the person's medicine names, whose strengths ("Glycomet 500") are part of the name, not values."""
    try:
        answer = Answer.model_validate_json(raw)
    except ValidationError as e:
        return None, [f"answer does not match the schema: {e.errors()[0]['msg']}"]

    by_id = {e.id: e.text for e in evidence}
    everything = "\n".join(by_id.values())
    errors = []

    free_text = [("summary", answer.summary), ("doctor_note", answer.doctor_note)]
    free_text += [(f"missing_info {i}", t) for i, t in enumerate(answer.missing_info, 1)]
    for field, text in free_text:
        errors += [f"{field} states {n}, which is not in the evidence"
                   for n in _unsupported(_without_names(text, names), everything)]

    for i, claim in enumerate(answer.claims, 1):
        if not claim.evidence_ids:
            errors.append(f"claim {i} cites no evidence")
            continue
        unknown = [eid for eid in claim.evidence_ids if eid not in by_id]
        if unknown:
            errors += [f"claim {i} cites unknown evidence {eid}" for eid in unknown]
            continue
        cited = "\n".join(by_id[eid] for eid in claim.evidence_ids)
        errors += [f"claim {i} states {n}, which is not in its evidence"
                   for n in _unsupported(_without_names(claim.text, names), cited)]

    for field, text in free_text + [(f"claim {i}", c.text) for i, c in enumerate(answer.claims, 1)]:
        if phrase := advice_phrase(text):
            errors.append(f"{field} gives medical advice ('{phrase.lower()}')")

    return answer, errors
