"""Lab test dictionary and name matching (plan 8.1, 8.2).

Deviation from the plan: no token_set_ratio. It scores 100 whenever one name's words are a
subset of another's, so "Mean Corpuscular Haemoglobin" -> Haemoglobin and "Non-HDL" -> HDL.
Fuzzy matching here only forgives typos inside words (OCR "Haemoglobln"), never extra or
missing words. An unmapped row is safe; a wrongly mapped one puts a wrong value on a chart.
"""
import csv
import re
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from rapidfuzz import fuzz

from app.services.labs.values import normalize_unit

FUZZY_MIN_SCORE = 90
FUZZY_MIN_TOKEN_SCORE = 88  # "vldl" vs "ldl" is 86: rejected

# Specimen and method words that don't change which test it is.
_DROP_WORDS = {"s", "serum", "plasma", "direct", "calculated", "calc", "ultrasensitive", "ultra", "sensitive",
               "level", "levels", "test", "estimation"}
_BRACKET_RE = re.compile(r"\(([^)]*)\)")


@dataclass(frozen=True)
class LabTest:
    loinc_code: str
    canonical_name: str
    display_name_hi: str
    canonical_unit: str
    category: str


@dataclass(frozen=True)
class Match:
    test: LabTest
    score: float  # 100 for an exact alias


def normalize_name(raw: str) -> tuple[str, str | None]:
    """Returns (main name, bracket content) both normalised; bracket is None if absent or empty."""
    s = raw.lower().replace("haemo", "hemo")
    bracket = _BRACKET_RE.search(s)
    main = _clean(_BRACKET_RE.sub(" ", s))
    second = _clean(bracket.group(1)) if bracket else ""
    return main, (second or None)


def _clean(s: str) -> str:
    words = re.sub(r"[^a-z0-9]+", " ", s).split()
    return " ".join(w for w in words if w not in _DROP_WORDS)


class LabDictionary:
    def __init__(self, tests: list[LabTest], aliases: dict[str, str], conversions: dict[tuple[str, str], tuple]):
        self.tests = {t.loinc_code: t for t in tests}
        self.aliases = {alias: self.tests[code] for alias, code in aliases.items()}
        self._conversions = conversions  # (loinc, from_unit) -> (multiplier, offset)

    @classmethod
    def from_csv(cls, seed_dir: Path) -> "LabDictionary":
        tests = [LabTest(**row) for row in _read(seed_dir / "lab_tests.csv")]
        aliases = {normalize_name(r["alias"])[0]: r["loinc_code"] for r in _read(seed_dir / "aliases.csv")}
        conversions = {
            (r["loinc_code"], normalize_unit(r["from_unit"])): (Decimal(r["multiplier"]), Decimal(r["offset"]))
            for r in _read(seed_dir / "unit_conversions.csv")
        }
        return cls(tests, aliases, conversions)

    @property
    def alias_count(self) -> int:
        return len(self.aliases)

    def match(self, raw_name: str) -> Match | None:
        candidates = [c for c in normalize_name(raw_name) if c]
        for c in candidates:
            if c in self.aliases:
                return Match(self.aliases[c], 100)
        for c in candidates:
            if m := self._fuzzy(c):
                return m
        return None

    def _fuzzy(self, name: str) -> Match | None:
        tokens = sorted(name.split())
        best: Match | None = None
        for alias, test in self.aliases.items():
            alias_tokens = sorted(alias.split())
            if len(alias_tokens) != len(tokens):
                continue
            if any(fuzz.ratio(a, b) < FUZZY_MIN_TOKEN_SCORE for a, b in zip(tokens, alias_tokens)):
                continue
            score = fuzz.ratio(" ".join(tokens), " ".join(alias_tokens))
            if score >= FUZZY_MIN_SCORE and (best is None or score > best.score):
                best = Match(test, score)
        return best

    def conversion(self, loinc_code: str, unit: str | None) -> tuple[Decimal, Decimal] | None:
        """(multiplier, offset) to reach the canonical unit, or None if we can't convert."""
        unit = normalize_unit(unit)
        if unit == self.tests[loinc_code].canonical_unit:
            return Decimal(1), Decimal(0)
        return self._conversions.get((loinc_code, unit))


def _read(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))
