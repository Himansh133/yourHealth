"""Synthetic patients with health stories (plan 14.2 step 1). No real patient data.

Each patient follows a story: values move the way the story says (e.g. HbA1c falls after metformin starts) plus
small random noise. Everything is drawn from one seeded random generator, so a seed gives the same dataset.
"""
import random
from dataclasses import dataclass, field
from datetime import date, timedelta


@dataclass(frozen=True)
class TestSpec:
    loinc: str
    unit: str  # canonical unit, as in refdata/seed/lab_tests.csv
    low: float | None
    high: float | None
    decimals: int
    low_female: float | None = None  # sex-specific ranges, where they differ
    high_female: float | None = None

    def range_for(self, sex: str) -> tuple[float | None, float | None]:
        if sex == "female" and (self.low_female is not None or self.high_female is not None):
            return self.low_female, self.high_female
        return self.low, self.high


TESTS = {t.loinc: t for t in [
    TestSpec("4548-4", "%", 4.0, 5.6, 1),
    TestSpec("1558-6", "mg/dL", 70, 100, 0),
    TestSpec("3016-3", "µIU/mL", 0.4, 4.5, 2),
    TestSpec("3024-7", "ng/dL", 0.8, 1.8, 2),
    TestSpec("718-7", "g/dL", 13.0, 17.0, 1, 12.0, 15.0),
    TestSpec("2093-3", "mg/dL", None, 200, 0),
    TestSpec("13457-7", "mg/dL", None, 100, 0),
    TestSpec("2085-9", "mg/dL", 40, None, 0),
    TestSpec("2571-8", "mg/dL", None, 150, 0),
    TestSpec("2160-0", "mg/dL", 0.7, 1.3, 2),
    TestSpec("3084-1", "mg/dL", 3.5, 7.2, 1),
    TestSpec("1742-6", "U/L", 7, 56, 0),
    TestSpec("1920-8", "U/L", 10, 40, 0),
    TestSpec("62292-8", "ng/mL", 30, 100, 1),
    TestSpec("2132-9", "pg/mL", 211, 911, 0),
    TestSpec("2951-2", "mmol/L", 135, 145, 0),
    TestSpec("2823-3", "mmol/L", 3.5, 5.1, 1),
    TestSpec("2157-6", "U/L", 30, 200, 0),
]}

PANELS = {
    "diabetes": ["4548-4", "1558-6"],
    "thyroid": ["3016-3", "3024-7"],
    "lipid": ["2093-3", "13457-7", "2085-9", "2571-8"],
    "kidney": ["2160-0", "3084-1"],
    "liver": ["1742-6", "1920-8"],
    "vitamins": ["62292-8", "2132-9"],
    "electrolytes": ["2951-2", "2823-3"],
    "cbc": ["718-7"],
    "ck": ["2157-6"],
}

HEALTHY = {"4548-4": 5.2, "1558-6": 88, "3016-3": 2.1, "3024-7": 1.2, "718-7": 14.2, "2093-3": 170, "13457-7": 85,
           "2085-9": 52, "2571-8": 110, "2160-0": 0.9, "3084-1": 5.0, "1742-6": 24, "1920-8": 22, "62292-8": 42,
           "2132-9": 480, "2951-2": 140, "2823-3": 4.3, "2157-6": 110}


def _towards(start: float, end: float, months_on: float, months_to_settle: float) -> float:
    """Moves from start to end over months_to_settle once a medicine is taken; flat before it."""
    if months_on <= 0:
        return start
    return start + (end - start) * min(months_on / months_to_settle, 1.0)


# story -> (panels tested, medicines as (brand, month started), month -> {loinc: true value})
def _diabetic(m_on: dict[str, float]) -> dict[str, float]:
    on = m_on["Glycomet 500"]
    return {**HEALTHY, "4548-4": _towards(8.6, 6.8, on, 6), "1558-6": _towards(165, 115, on, 3),
            "2132-9": max(HEALTHY["2132-9"] - 12 * max(on, 0), 190)}


def _hypothyroid(m_on: dict[str, float]) -> dict[str, float]:
    return {**HEALTHY, "3016-3": _towards(9.4, 2.8, m_on["Thyronorm 50"], 3),
            "3024-7": _towards(0.65, 1.25, m_on["Thyronorm 50"], 3),
            "62292-8": _towards(13.5, 34, m_on["Uprise D3 60K"], 4)}


def _hypertensive(m_on: dict[str, float]) -> dict[str, float]:
    on = m_on["Telma H"]
    return {**HEALTHY, "2951-2": _towards(140, 133, on, 8), "2823-3": _towards(4.4, 3.3, on, 8),
            "2160-0": _towards(1.0, 1.15, on, 8)}


def _statin(m_on: dict[str, float]) -> dict[str, float]:
    on = m_on["Atorva 10"]
    return {**HEALTHY, "2093-3": _towards(242, 178, on, 3), "13457-7": _towards(162, 94, on, 3),
            "2085-9": 41, "2571-8": _towards(215, 160, on, 3), "1742-6": _towards(28, 39, on, 3)}


def _gout(m_on: dict[str, float]) -> dict[str, float]:
    return {**HEALTHY, "3084-1": _towards(9.1, 5.6, m_on["Zyloric 100"], 4)}


def _healthy(m_on: dict[str, float]) -> dict[str, float]:
    return dict(HEALTHY)


STORIES = {
    "diabetic_metformin": (["diabetes", "kidney", "vitamins"], [("Glycomet 500", 3)], _diabetic),
    "hypothyroid": (["thyroid", "vitamins"], [("Thyronorm 50", 1), ("Uprise D3 60K", 2)], _hypothyroid),
    "hypertensive_diuretic": (["electrolytes", "kidney"], [("Telma H", 2)], _hypertensive),
    "statin": (["lipid", "liver", "ck"], [("Atorva 10", 1)], _statin),
    "gout": (["kidney"], [("Zyloric 100", 2)], _gout),
    "healthy": (["diabetes", "lipid", "cbc"], [], _healthy),
}

PEOPLE = [("Papa", "male", 58), ("Mummy", "female", 54), ("Dadi", "female", 76), ("Dada", "male", 79),
          ("Nana", "male", 72), ("Nani", "female", 69), ("Chacha", "male", 50), ("Bua", "female", 47),
          ("Mama", "male", 45), ("Mausi", "female", 49), ("Bhaiya", "male", 31), ("Didi", "female", 33)]


@dataclass(frozen=True)
class Medicine:
    brand: str
    started_on: date


@dataclass(frozen=True)
class Report:
    collected_on: date
    values: dict[str, float]  # loinc -> value in the canonical unit, already rounded as a lab would print it


@dataclass(frozen=True)
class Patient:
    key: str  # e.g. "papa_01"
    display_name: str
    sex: str
    birth_year: int
    story: str
    medicines: list[Medicine] = field(default_factory=list)
    reports: list[Report] = field(default_factory=list)


def generate_patients(seed: int = 1, n: int = 30) -> list[Patient]:
    rng = random.Random(seed)
    story_names = list(STORIES)
    patients = []
    for i in range(n):
        name, sex, age = PEOPLE[i % len(PEOPLE)]
        story = story_names[i % len(story_names)]
        panels, meds, trajectory = STORIES[story]
        first = date(2024, 1, 1) + timedelta(days=rng.randrange(0, 540))
        visit_months = [0.0]
        for _ in range(rng.randint(2, 5)):
            visit_months.append(visit_months[-1] + rng.uniform(2, 4.5))
        # The first visit is always before any medicine, so stories have a "before".
        started = {brand: first + timedelta(days=round(month * 30.4) + rng.randint(5, 20)) for brand, month in meds}

        reports = []
        for month in visit_months:
            on = first + timedelta(days=round(month * 30.4))
            months_on = {brand: (on - start).days / 30.4 for brand, start in started.items()}
            truth = trajectory(months_on)
            tested = [loinc for panel in panels for loinc in PANELS[panel]]
            values = {}
            for loinc in tested:
                spec = TESTS[loinc]
                v = truth[loinc] * (1 + rng.gauss(0, 0.02))
                if story == "healthy":  # keep healthy people inside every range
                    low, high = spec.range_for(sex)
                    v = min(max(v, low if low is not None else v), high if high is not None else v)
                values[loinc] = round(v, spec.decimals)
            reports.append(Report(on, values))

        patients.append(Patient(
            key=f"{name.lower()}_{i + 1:02d}", display_name=name, sex=sex, birth_year=2026 - age - rng.randint(0, 3),
            story=story, medicines=[Medicine(b, d) for b, d in started.items()], reports=reports))
    return patients
