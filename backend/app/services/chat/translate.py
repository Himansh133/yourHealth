"""Hindi output (plan 11): translate an answer that already passed the validator, then check nothing changed.

The answer is written and validated in English (the advice-phrase checks are most reliable there), translated with a
glossary, and accepted only if every field keeps exactly the same numbers, uses digits 0-9 and adds no advice.
One retry; then None, and the caller shows English.
"""
import json
import re
from collections import Counter
from decimal import Decimal
from functools import lru_cache

from app.core.config import settings
from app.services.chat.llm import LLM, LLMError
from app.services.chat.validator import NUMBER, Answer, Claim, advice_phrase

DEVANAGARI_DIGIT = re.compile(r"[०-९]")

SYSTEM = """Translate the values of this JSON into simple, spoken Hindi in Devanagari, as a family would talk.
Rules:
1. Keep test names, medicine names and units in English letters exactly as written (TSH, HbA1c, Glycomet, mg/dL).
2. The first time a test is mentioned, add its Hindi meaning in brackets, from this list:
{tests}
3. Keep every number exactly as written, with digits 0-9. Dates: keep the day and year digits as they are.
4. Use these words: {words}
5. Do not add, remove or change any fact, number or advice.
Reply with JSON only, in the same shape: {{"summary": str, "claims": [str, ...], "missing_info": [str, ...], "doctor_note": str}},
with claims and missing_info in the same order and of the same length."""


@lru_cache
def general_glossary() -> dict[str, str]:
    return json.loads((settings.refdata_dir / "glossary_hi.json").read_text(encoding="utf-8"))


def numbers_match(english: str, hindi: str) -> bool:
    """Same numbers, the same number of times (digits inside names like HbA1c don't count)."""
    return Counter(map(Decimal, NUMBER.findall(english))) == Counter(map(Decimal, NUMBER.findall(hindi)))


def _problems(en: Answer, out: dict, glosses: list[str]) -> list[str]:
    """glosses: our glossary's test names and Hindi meanings; numbers inside them ("Vitamin D, 25-OH total",
    "पिछले 3 महीने") weren't added or dropped by the model, so they are set aside on both sides."""
    try:
        pairs = [(en.summary, out["summary"]), (en.doctor_note, out["doctor_note"])]
        if len(out["claims"]) != len(en.claims) or len(out["missing_info"]) != len(en.missing_info):
            return ["claims or missing_info changed length"]
        pairs += list(zip([c.text for c in en.claims], out["claims"])) + list(zip(en.missing_info, out["missing_info"]))
    except (KeyError, TypeError):
        return ["wrong JSON shape"]
    problems = []
    for english, hindi in pairs:
        if not isinstance(hindi, str):
            return ["wrong JSON shape"]
        if DEVANAGARI_DIGIT.search(hindi):
            problems.append(f"use digits 0-9: {hindi!r}")
        elif not numbers_match(_without(english, glosses), _without(hindi, glosses)):
            problems.append(f"numbers changed: {english!r} -> {hindi!r}")
        if advice_phrase(hindi):
            problems.append(f"added advice: {hindi!r}")
    return problems


def _without(text: str, glosses: list[str]) -> str:
    for g in glosses:
        text = text.replace(g, "")
    return text


def translate_answer(llm: LLM, en: Answer, glossary: dict[str, str]) -> Answer | None:
    """glossary: test name -> Hindi meaning, for the tests in this answer."""
    tests = "\n".join(f"{name} = {meaning}" for name, meaning in glossary.items()) or "(none)"
    words = ", ".join(f"{en_word} = {hi}" for en_word, hi in general_glossary().items())
    system = SYSTEM.format(tests=tests, words=words)
    user = json.dumps({"summary": en.summary, "claims": [c.text for c in en.claims], "missing_info": en.missing_info,
                       "doctor_note": en.doctor_note}, ensure_ascii=False)
    for attempt in range(2):
        try:
            out = json.loads(llm.complete_json(system, user))
        except (LLMError, ValueError):
            continue
        glosses = sorted({*glossary, *glossary.values()}, key=len, reverse=True)  # longest first
        problems = _problems(en, out, glosses) if isinstance(out, dict) else ["wrong JSON shape"]
        if not problems:
            return Answer(answerable=en.answerable, summary=out["summary"], doctor_note=out["doctor_note"],
                          missing_info=out["missing_info"],
                          claims=[Claim(text=t, evidence_ids=c.evidence_ids) for t, c in zip(out["claims"], en.claims)])
        if attempt == 0:
            user += "\n\nYour previous translation was rejected:\n- " + "\n- ".join(problems[:5])
    return None
