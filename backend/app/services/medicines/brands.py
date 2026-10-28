"""Indian brand search and matching (plan 9.1, 9.2).

Matching prescription text to a brand forgives spelling slips in the name only. The strength numbers
must be identical: "Telma 60" must never snap to "Telma 40" or "Telma 80".
"""
import csv
import re
from dataclasses import dataclass
from pathlib import Path

from rapidfuzz import fuzz

from app.services.medicines.composition import Component, parse_composition

SEARCH_LIMIT = 10
SEARCH_MIN_SCORE = 80
MATCH_MIN_SCORE = 85
_UNIT_WORDS = {"mg", "mcg", "ml", "g", "iu"}


@dataclass(frozen=True)
class Brand:
    brand_name: str
    normalized: str
    composition_raw: str
    components: tuple[Component, ...]
    source: str


def normalize_brand(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", " ", text.lower())
    s = re.sub(r"(?<=[a-z])(?=\d)|(?<=\d)(?=[a-z])", " ", s)  # "gp1" -> "gp 1", "500mg" -> "500 mg"
    return " ".join(w for w in s.split() if w not in _UNIT_WORDS)


def _split(normalized: str) -> tuple[str, list[str]]:
    words = normalized.split()
    return " ".join(w for w in words if not w.isdigit()), sorted(w for w in words if w.isdigit())


class BrandIndex:
    def __init__(self, brands: list[Brand]):
        self.brands = brands

    @classmethod
    def from_rows(cls, rows: list[tuple[str, str, str]]) -> "BrandIndex":
        """(brand_name, composition_raw, source) rows, e.g. from the drug_brands table."""
        return cls([Brand(n, normalize_brand(n), c, tuple(parse_composition(c)), s) for n, c, s in rows])

    @classmethod
    def from_csv(cls, path: Path) -> "BrandIndex":
        with path.open(encoding="utf-8") as f:
            return cls([
                Brand(r["brand_name"], normalize_brand(r["brand_name"]), r["composition_raw"],
                      tuple(parse_composition(r["composition_raw"])), r["source"])
                for r in csv.DictReader(f)
            ])

    def search(self, query: str) -> list[Brand]:
        """Autocomplete: prefix matches, then substring, then typo-tolerant matches."""
        q = normalize_brand(query)
        if not q:
            return []
        scored = []
        for i, b in enumerate(self.brands):
            if b.normalized.startswith(q):
                scored.append((0, 0, i, b))
            elif q in b.normalized:
                scored.append((1, 0, i, b))
            elif (score := fuzz.partial_ratio(q, b.normalized)) >= SEARCH_MIN_SCORE:
                scored.append((2, -score, i, b))
        return [b for *_, b in sorted(scored)[:SEARCH_LIMIT]]

    def match(self, text: str) -> Brand | None:
        """Best brand for a prescription line's brand text, or None if unsure."""
        name, nums = _split(normalize_brand(text))
        best, best_score = None, 0.0
        for b in self.brands:
            b_name, b_nums = _split(b.normalized)
            if b_nums != nums:
                continue
            score = fuzz.ratio(name, b_name)
            if score >= MATCH_MIN_SCORE and score > best_score:
                best, best_score = b, score
        return best
