from decimal import Decimal
from pathlib import Path

import pytest

from app.services.labs.dictionary import LabDictionary, normalize_name

SEED = Path(__file__).resolve().parents[2] / "refdata" / "seed"


@pytest.fixture(scope="module")
def d():
    return LabDictionary.from_csv(SEED)


# --- normalize_name ----------------------------------------------------------

def test_normalize_lowercases_and_haemo_to_hemo():
    assert normalize_name("Glycated Haemoglobin") == ("glycated hemoglobin", None)


def test_normalize_splits_bracket_content_into_second_candidate():
    assert normalize_name("HbA1c (Glycosylated Haemoglobin)") == ("hba1c", "glycosylated hemoglobin")


def test_normalize_strips_punctuation_and_specimen_prefix():
    assert normalize_name("S. Creatinine") == ("creatinine", None)
    assert normalize_name("Serum Uric Acid") == ("uric acid", None)


def test_normalize_drops_method_words():
    assert normalize_name("TSH - Ultrasensitive") == ("tsh", None)
    assert normalize_name("LDL Cholesterol, Direct") == ("ldl cholesterol", None)


# --- matching: common spellings map ------------------------------------------

@pytest.mark.parametrize("raw,expected", [
    ("HbA1c", "HbA1c"),
    ("HbA1c (Glycosylated Haemoglobin)", "HbA1c"),
    ("Glycated Haemoglobin (HbA1c)", "HbA1c"),
    ("Glucose - Fasting", "Fasting glucose"),
    ("Fasting Blood Sugar (FBS)", "Fasting glucose"),
    ("Plasma Glucose Fasting", "Fasting glucose"),
    ("TSH", "TSH"),
    ("Thyroid Stimulating Hormone (TSH) - Ultrasensitive", "TSH"),
    ("Free T4 (FT4)", "Free T4"),
    ("Haemoglobin", "Haemoglobin"),
    ("Hemoglobin (Hb)", "Haemoglobin"),
    ("Cholesterol, Total", "Total cholesterol"),
    ("Serum Cholesterol", "Total cholesterol"),
    ("HDL Cholesterol - Direct", "HDL cholesterol"),
    ("LDL Cholesterol (Calculated)", "LDL cholesterol (calculated)"),
    ("Triglycerides", "Triglycerides"),
    ("S. Creatinine", "Creatinine"),
    ("Serum Uric Acid", "Uric acid"),
    ("SGPT", "ALT (SGPT)"),
    ("ALT (SGPT)", "ALT (SGPT)"),
    ("Alanine Aminotransferase", "ALT (SGPT)"),
    ("SGOT (AST)", "AST (SGOT)"),
    ("25-OH Vitamin D", "Vitamin D, 25-OH total"),
    ("Vitamin D (25-Hydroxy)", "Vitamin D, 25-OH total"),
    ("Vitamin B12", "Vitamin B12"),
    ("Sodium (Na+)", "Sodium"),
    ("Potassium", "Potassium"),
    ("CPK", "Creatine kinase (CK)"),
])
def test_maps_common_spellings(d, raw, expected):
    match = d.match(raw)
    assert match is not None, raw
    assert match.test.canonical_name == expected


def test_exact_alias_has_full_score(d):
    assert d.match("SGPT").score == 100


@pytest.mark.parametrize("raw,expected", [
    ("Haemoglobln", "Haemoglobin"),        # OCR i -> l
    ("Triglycerdes", "Triglycerides"),     # dropped letter
    ("Creatinlne", "Creatinine"),
])
def test_fuzzy_catches_ocr_typos(d, raw, expected):
    match = d.match(raw)
    assert match is not None and match.test.canonical_name == expected
    assert 90 <= match.score < 100


# --- matching: lookalikes must NOT map (wrong mapping = wrong value on a chart) ---

@pytest.mark.parametrize("raw", [
    "Mean Corpuscular Haemoglobin",    # MCH, not Hb
    "MCHC",
    "Non-HDL Cholesterol",             # not HDL
    "VLDL Cholesterol",                # not LDL
    "T4",                              # total T4, not free T4
    "Thyroxine (T4), Total",
    "Post Prandial Blood Sugar",       # not fasting glucose
    "Glucose - Random",
    "Urine Creatinine",                # not serum creatinine
    "Vitamin B6",
    "Total Protein",
    "",
])
def test_lookalikes_stay_unmapped(d, raw):
    assert d.match(raw) is None, raw


# --- reference data ----------------------------------------------------------

def test_every_alias_points_to_a_known_test(d):
    assert d.alias_count > 50
    for alias, test in d.aliases.items():
        assert test.loinc_code in d.tests


def test_conversion_lookup(d):
    hba1c = d.match("HbA1c").test
    multiplier, offset = d.conversion(hba1c.loinc_code, "mmol/mol")
    assert (multiplier, offset) == (Decimal("0.09152"), Decimal("2.15"))


def test_no_conversion_needed_for_canonical_unit(d):
    hba1c = d.match("HbA1c").test
    assert d.conversion(hba1c.loinc_code, "%") == (Decimal(1), Decimal(0))


def test_unknown_unit_has_no_conversion(d):
    hba1c = d.match("HbA1c").test
    assert d.conversion(hba1c.loinc_code, "furlongs") is None
