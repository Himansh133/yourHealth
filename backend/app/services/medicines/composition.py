"""Parse a composition string like "Metformin (500mg) + Glimepiride (1mg)" (plan 9.2)."""
import re
from dataclasses import dataclass
from decimal import Decimal

_PART_RE = re.compile(
    r"^(?P<name>.*?[a-z].*?)\s*\(?\s*(?P<num>\d+(?:\.\d+)?)\s*(?P<unit>mg|mcg|µg|g|ml|iu)\s*\)?\s*$", re.IGNORECASE
)
# Salt forms are dropped so "Levothyroxine Sodium" and "levothyroxine" are the same ingredient.
_SALTS = {"hydrochloride", "hcl", "sodium", "potassium", "calcium", "besylate", "besilate", "phosphate"}


@dataclass(frozen=True)
class Component:
    ingredient: str
    strength: Decimal | None
    unit: str | None


def parse_composition(raw: str) -> list[Component]:
    components = []
    for part in (p.strip() for p in raw.split("+")):
        if not part:
            continue
        m = _PART_RE.match(part)
        name = m["name"] if m else part
        strength = Decimal(m["num"]) if m else None
        unit = _unit(m["unit"]) if m else None
        components.append(Component(ingredient_name(name), strength, unit))
    return components


def ingredient_name(name: str) -> str:
    words = re.sub(r"[^a-z ]", " ", name.lower()).split()
    while len(words) > 1 and words[-1] in _SALTS:
        words.pop()
    return " ".join(words)


def _unit(u: str) -> str:
    u = u.lower()
    return {"iu": "IU", "µg": "mcg"}.get(u, u)
