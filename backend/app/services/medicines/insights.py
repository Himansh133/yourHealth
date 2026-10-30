"""'Is this medicine doing its job?' (plan 9.5). Shows data around a medicine's start date; never claims cause.

Compares the last value before the start date with the latest value after start + onset window (e.g. HbA1c
needs about 3 months), ignoring anything after the medicine was stopped. The plan (9.5) said "first after"; the
latest is used so the card agrees with the doctor sheet's flagged values (PROBLEMS_FACED 7.7).
"""
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal


@dataclass(frozen=True)
class Medicine:
    id: str
    name: str  # as the user knows it, e.g. "Glycomet 500"
    ingredient: str
    started_on: date | None
    stopped_on: date | None


@dataclass(frozen=True)
class Effect:
    ingredient: str
    loinc_code: str
    test_name: str
    unit: str
    direction: str  # increase | decrease | either
    effect_type: str  # therapeutic | monitor
    onset_days: int
    note: str
    source_url: str
    source_section: str


@dataclass(frozen=True)
class Reading:
    id: str  # lab_result id, used as a citation
    loinc_code: str
    observed_on: date
    value: Decimal  # canonical unit


@dataclass(frozen=True)
class Insight:
    medicine_id: str
    medicine_name: str
    ingredient: str
    loinc_code: str
    test_name: str
    unit: str
    effect_type: str
    direction: str
    status: str  # matches_expected | not_as_expected | watch | no_change_seen | not_enough_data | no_start_date
    flagged: bool  # goes on the doctor visit sheet
    before: Reading | None
    after: Reading | None
    message: str
    note: str
    source_url: str
    source_section: str


def compute_insights(medicines: list[Medicine], effects: list[Effect], readings: list[Reading]) -> list[Insight]:
    out = []
    for med in medicines:
        for eff in (e for e in effects if e.ingredient == med.ingredient):
            series = sorted((r for r in readings if r.loinc_code == eff.loinc_code), key=lambda r: r.observed_on)
            out.append(_insight(med, eff, series))
    return out


def _insight(med: Medicine, eff: Effect, series: list[Reading]) -> Insight:
    def make(status, message, flagged=False, before=None, after=None):
        return Insight(med.id, med.name, med.ingredient, eff.loinc_code, eff.test_name, eff.unit, eff.effect_type,
                       eff.direction, status, flagged, before, after, message, eff.note, eff.source_url,
                       eff.source_section)

    if med.started_on is None:
        return make("no_start_date", f"Add the date you started {med.name} to compare {eff.test_name} before and after.")

    window_start = med.started_on + timedelta(days=eff.onset_days)
    before = next((r for r in reversed(series) if r.observed_on < med.started_on), None)
    after = next((r for r in reversed(series) if r.observed_on >= window_start
                  and (med.stopped_on is None or r.observed_on <= med.stopped_on)), None)
    if before is None or after is None:
        return make("not_enough_data",
                    f"Not enough {eff.test_name} reports before and after starting {med.ingredient} to compare.")

    change = (f"{eff.test_name} went from {_v(before, eff)} ({_d(before.observed_on)}) "
              f"to {_v(after, eff)} ({_d(after.observed_on)})")
    moved = "decrease" if after.value < before.value else "increase" if after.value > before.value else "none"
    expected = moved == eff.direction or (eff.direction == "either" and moved != "none")
    started = f"after {med.ingredient} was started in {med.started_on.strftime('%b %Y')}"

    if eff.effect_type == "therapeutic":
        if expected:
            return make("matches_expected", f"{change} {started}. This matches the expected effect of {med.ingredient}.",
                        before=before, after=after)
        return make("not_as_expected", f"{change} {started}. Worth discussing with your doctor.", True, before, after)

    verb = {"decrease": "lower", "increase": "raise"}.get(eff.direction, "change")
    if expected:
        return make("watch", f"{med.ingredient.capitalize()} is known to {verb} {eff.test_name} over time. "
                             f"{change}. Worth mentioning to your doctor.", True, before, after)
    return make("no_change_seen", f"{change} since starting {med.ingredient}.", before=before, after=after)


def _v(r: Reading, eff: Effect) -> str:
    return f"{format(r.value.normalize(), 'f')} {eff.unit}"


def _d(d: date) -> str:
    return f"{d.day} {d.strftime('%b %Y')}"
