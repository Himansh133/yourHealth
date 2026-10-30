import re
from datetime import date
from decimal import Decimal

from app.services.medicines.insights import Effect, Medicine, Reading, compute_insights

METFORMIN = Medicine(id="m1", name="Glycomet 500", ingredient="metformin", started_on=date(2026, 3, 1), stopped_on=None)


def effect(loinc="4548-4", test="HbA1c", unit="%", direction="decrease", kind="therapeutic", onset_days=90):
    return Effect(ingredient="metformin", loinc_code=loinc, test_name=test, unit=unit, direction=direction,
                  effect_type=kind, onset_days=onset_days, note="note", source_url="https://dailymed/x",
                  source_section="indications_and_usage")


def r(loinc, on, value, rid=None):
    return Reading(id=rid or f"{loinc}-{on}", loinc_code=loinc, observed_on=on, value=Decimal(value))


def test_therapeutic_effect_in_expected_direction_matches():
    readings = [r("4548-4", date(2026, 1, 10), "8.1", "jan"), r("4548-4", date(2026, 6, 14), "7.2", "jun")]
    [ins] = compute_insights([METFORMIN], [effect()], readings)
    assert ins.status == "matches_expected"
    assert (ins.before.id, ins.after.id) == ("jan", "jun")
    assert ins.flagged is False
    assert ins.message == ("HbA1c went from 8.1 % (10 Jan 2026) to 7.2 % (14 Jun 2026) after metformin was started "
                           "in Mar 2026. This matches the expected effect of metformin.")


def test_value_inside_onset_window_is_not_used():
    # one week after starting is too early for HbA1c (about 3 months)
    readings = [r("4548-4", date(2026, 1, 10), "8.1"), r("4548-4", date(2026, 3, 8), "8.0"),
                r("4548-4", date(2026, 6, 14), "7.2", "jun")]
    [ins] = compute_insights([METFORMIN], [effect()], readings)
    assert ins.after.id == "jun"


def test_therapeutic_effect_not_seen_is_neutral():
    readings = [r("4548-4", date(2026, 1, 10), "7.0"), r("4548-4", date(2026, 6, 14), "7.6")]
    [ins] = compute_insights([METFORMIN], [effect()], readings)
    assert ins.status == "not_as_expected"
    assert ins.flagged is True
    assert "HbA1c went from 7 % (10 Jan 2026) to 7.6 % (14 Jun 2026)" in ins.message
    assert "Worth discussing with your doctor." in ins.message


def test_monitored_value_moving_the_watched_way_is_flagged():
    b12 = effect(loinc="2132-9", test="Vitamin B12", unit="pg/mL", kind="monitor", onset_days=180)
    readings = [r("2132-9", date(2025, 12, 1), "410"), r("2132-9", date(2027, 9, 1), "260")]
    [ins] = compute_insights([METFORMIN], [b12], readings)
    assert ins.status == "watch"
    assert ins.flagged is True
    assert ins.message == ("Metformin is known to lower Vitamin B12 over time. Vitamin B12 went from 410 pg/mL "
                           "(1 Dec 2025) to 260 pg/mL (1 Sep 2027). Worth mentioning to your doctor.")


def test_monitored_value_steady_is_not_flagged():
    b12 = effect(loinc="2132-9", test="Vitamin B12", unit="pg/mL", kind="monitor", onset_days=180)
    readings = [r("2132-9", date(2025, 12, 1), "410"), r("2132-9", date(2027, 9, 1), "455")]
    [ins] = compute_insights([METFORMIN], [b12], readings)
    assert (ins.status, ins.flagged) == ("no_change_seen", False)


def test_not_enough_data_without_a_before_value():
    [ins] = compute_insights([METFORMIN], [effect()], [r("4548-4", date(2026, 6, 14), "7.2")])
    assert ins.status == "not_enough_data"
    assert ins.before is None and ins.flagged is False
    assert ins.message == "Not enough HbA1c reports before and after starting metformin to compare."


def test_without_start_date_says_so():
    med = Medicine(id="m1", name="Glycomet 500", ingredient="metformin", started_on=None, stopped_on=None)
    [ins] = compute_insights([med], [effect()], [])
    assert ins.status == "no_start_date"
    assert "Add the date you started" in ins.message


def test_values_after_stopping_are_ignored():
    med = Medicine(id="m1", name="Glycomet 500", ingredient="metformin",
                   started_on=date(2026, 3, 1), stopped_on=date(2026, 5, 1))
    readings = [r("4548-4", date(2026, 1, 10), "8.1"), r("4548-4", date(2026, 9, 1), "8.4")]
    [ins] = compute_insights([med], [effect()], readings)
    assert ins.status == "not_enough_data"


def test_only_effects_of_the_medicines_ingredients():
    statin = Effect(ingredient="atorvastatin", loinc_code="13457-7", test_name="LDL", unit="mg/dL",
                    direction="decrease", effect_type="therapeutic", onset_days=28, note="", source_url="",
                    source_section="")
    assert compute_insights([METFORMIN], [statin], []) == []


def test_wording_never_claims_cause_or_gives_advice():
    readings = [r("4548-4", date(2026, 1, 10), "8.1"), r("4548-4", date(2026, 6, 14), "7.2"),
                r("2132-9", date(2025, 12, 1), "410"), r("2132-9", date(2027, 9, 1), "260")]
    effects = [effect(), effect(loinc="2132-9", test="Vitamin B12", unit="pg/mL", kind="monitor", onset_days=180)]
    for ins in compute_insights([METFORMIN], effects, readings):
        assert not re.search(r"caused|because of|is working|isn't working|stop taking|switch|increase the dose",
                             ins.message, re.IGNORECASE), ins.message


def test_the_latest_value_while_on_the_medicine_is_compared():
    # Found on a doctor sheet: sodium flagged low at 131 in the table, while this card said "142 to 140" from a value
    # 9 months older, because it took the first value after the onset window.
    hctz = Medicine(id="m2", name="Telma H", ingredient="hydrochlorothiazide", started_on=date(2025, 8, 16),
                    stopped_on=None)
    sodium = Effect(ingredient="hydrochlorothiazide", loinc_code="2951-2", test_name="Sodium", unit="mmol/L",
                    direction="decrease", effect_type="monitor", onset_days=14, note="", source_url="",
                    source_section="")
    readings = [r("2951-2", date(2025, 5, 27), "142", "may25"), r("2951-2", date(2025, 9, 3), "140", "sep25"),
                r("2951-2", date(2026, 3, 28), "131", "mar26"), r("2951-2", date(2026, 6, 18), "131", "jun26")]
    [ins] = compute_insights([hctz], [sodium], readings)
    assert (ins.before.id, ins.after.id) == ("may25", "jun26")
    assert "Sodium went from 142 mmol/L (27 May 2025) to 131 mmol/L (18 Jun 2026)" in ins.message
