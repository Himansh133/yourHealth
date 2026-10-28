from decimal import Decimal
from pathlib import Path

import pytest

from app.services.labs.dictionary import LabDictionary
from app.services.labs.normalize import normalize_row
from app.services.labs.row_parser import RawRow

SEED = Path(__file__).resolve().parents[2] / "refdata" / "seed"


@pytest.fixture(scope="module")
def d():
    return LabDictionary.from_csv(SEED)


def raw(name, value, unit=None, rng=None, flag=None):
    return RawRow(raw_name=name, raw_value=value, raw_unit=unit, raw_range=rng, printed_flag=flag)


def test_mapped_row_in_canonical_unit(d):
    r = normalize_row(raw("HbA1c", "7.2", "%", "4.0 - 5.6"), d)
    assert r.test.canonical_name == "HbA1c"
    assert (r.value_num, r.qualifier) == (Decimal("7.2"), None)
    assert (r.range_low, r.range_high) == (Decimal("4.0"), Decimal("5.6"))
    assert r.value_canonical == Decimal("7.2")
    assert (r.range_low_canonical, r.range_high_canonical) == (Decimal("4.0"), Decimal("5.6"))
    assert r.flag == "high"
    assert r.confidence == pytest.approx(0.85)


def test_converts_value_and_range_to_canonical_unit(d):
    r = normalize_row(raw("Fasting Glucose", "5.5", "mmol/L", "3.9 - 5.6"), d)
    assert r.value_canonical == pytest.approx(Decimal("99.088"))
    assert r.range_low_canonical == pytest.approx(Decimal("70.2624"))
    assert r.flag == "normal"


def test_hba1c_ifcc_converted_with_offset(d):
    r = normalize_row(raw("HbA1c", "53", "mmol/mol", "20 - 42"), d)
    assert round(r.value_canonical, 2) == Decimal("7.00")
    assert r.flag == "high"


def test_flag_uses_printed_range_in_raw_unit(d):
    r = normalize_row(raw("Vitamin B12", "180", "pg/mL", "211 - 911"), d)
    assert r.flag == "low"


def test_no_range_printed(d):
    r = normalize_row(raw("Creatinine", "1.1", "mg/dL"), d)
    assert r.flag == "no_range"
    assert r.range_low is None and r.range_high_canonical is None


def test_unknown_unit_keeps_raw_value_but_no_canonical(d):
    r = normalize_row(raw("HbA1c", "7.2", "furlongs", "4.0 - 5.6"), d)
    assert r.value_num == Decimal("7.2")
    assert r.value_canonical is None
    assert r.flag == "high"  # range is in the same (raw) unit, so the flag still holds


def test_unit_missing_assumes_nothing(d):
    r = normalize_row(raw("HbA1c", "7.2", None, "4.0 - 5.6"), d)
    assert r.value_canonical is None


def test_qualifier_value(d):
    r = normalize_row(raw("TSH", "<0.01", "µIU/mL", "0.35 - 5.50"), d)
    assert (r.value_num, r.qualifier) == (Decimal("0.01"), "<")
    assert r.flag == "low"


# --- confidence (plan 7.3) -----------------------------------------------------

def test_unmapped_row_kept_with_lower_confidence(d):
    r = normalize_row(raw("Total Protein", "7.1", "g/dL", "6.0 - 8.3"), d)
    assert r.test is None
    assert r.value_canonical is None
    assert r.flag == "normal"
    assert r.confidence == pytest.approx(0.65)


def test_value_outside_sanity_range_lowers_confidence(d):
    # OCR read 7.2 as 72
    r = normalize_row(raw("HbA1c", "72", "%", "4.0 - 5.6"), d)
    assert r.confidence == pytest.approx(0.55)  # below 0.6 on its own: always reviewed


def test_printed_flag_disagreeing_with_computed_flag_lowers_confidence(d):
    r = normalize_row(raw("HbA1c", "7.2", "%", "4.0 - 5.6", flag="L"), d)
    assert r.flag == "high"
    assert r.confidence == pytest.approx(0.55)  # below 0.6 on its own: always reviewed


def test_printed_flag_agreeing_keeps_confidence(d):
    r = normalize_row(raw("HbA1c", "7.2", "%", "4.0 - 5.6", flag="H"), d)
    assert r.confidence == pytest.approx(0.85)


def test_ocr_confidence_multiplies(d):
    r = normalize_row(raw("HbA1c", "7.2", "%", "4.0 - 5.6"), d, ocr_confidence=0.9)
    assert r.confidence == pytest.approx(0.765)


def test_fuzzy_match_lowers_confidence_a_little(d):
    r = normalize_row(raw("Haemoglobln", "13.4", "g/dL", "13.0 - 17.0"), d)
    assert r.test.canonical_name == "Haemoglobin"
    assert r.confidence < 0.85


def test_confidence_never_negative(d):
    r = normalize_row(raw("Unknown Thing", "99999", "x", "1 - 2", flag="L"), d, ocr_confidence=0.3)
    assert 0 <= r.confidence < 0.6
