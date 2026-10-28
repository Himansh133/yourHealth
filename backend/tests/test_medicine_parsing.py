from decimal import Decimal
from pathlib import Path

import pytest

from app.services.medicines.brands import BrandIndex
from app.services.medicines.composition import Component, parse_composition
from app.services.medicines.prescription import RxLine, parse_prescription_line

SEED = Path(__file__).resolve().parents[2] / "refdata" / "seed"


# --- composition ----------------------------------------------------------------

@pytest.mark.parametrize("raw,expected", [
    ("Metformin (500mg)", [Component("metformin", Decimal("500"), "mg")]),
    ("Metformin (500mg) + Glimepiride (1mg)",
     [Component("metformin", Decimal("500"), "mg"), Component("glimepiride", Decimal("1"), "mg")]),
    ("Telmisartan 40 mg + Hydrochlorothiazide 12.5 mg",
     [Component("telmisartan", Decimal("40"), "mg"), Component("hydrochlorothiazide", Decimal("12.5"), "mg")]),
    ("Levothyroxine Sodium (50mcg)", [Component("levothyroxine", Decimal("50"), "mcg")]),
    ("Losartan Potassium (50mg)", [Component("losartan", Decimal("50"), "mg")]),
    ("Calcium Carbonate (500mg)", [Component("calcium carbonate", Decimal("500"), "mg")]),
    ("Cholecalciferol (60000 IU)", [Component("cholecalciferol", Decimal("60000"), "IU")]),
    ("Metformin", [Component("metformin", None, None)]),
    ("", []),
])
def test_parse_composition(raw, expected):
    assert parse_composition(raw) == expected


# --- brand index -----------------------------------------------------------------

@pytest.fixture(scope="module")
def brands():
    return BrandIndex.from_csv(SEED / "drug_brands.csv")


def test_search_prefix_first(brands):
    names = [b.brand_name for b in brands.search("glyco")]
    assert names[:4] == ["Glycomet 500", "Glycomet 850", "Glycomet GP 1", "Glycomet GP 2"]


def test_search_finds_all_brand_variants(brands):
    assert {b.brand_name for b in brands.search("telma")} == {"Telma 40", "Telma 80", "Telma H", "Telma AM"}


def test_search_tolerates_a_typo(brands):
    assert "Thyronorm 50" in [b.brand_name for b in brands.search("thyronrm")]


def test_search_empty_or_garbage(brands):
    assert brands.search("") == []
    assert brands.search("zzzzqqq") == []


def test_brand_components_come_from_composition(brands):
    [b] = [b for b in brands.search("glycomet gp 1")][:1]
    assert [c.ingredient for c in b.components] == ["metformin", "glimepiride"]


@pytest.mark.parametrize("text,expected", [
    ("Glycomet 500", "Glycomet 500"),
    ("GLYCOMET-500", "Glycomet 500"),
    ("Glycomett 500", "Glycomet 500"),      # OCR / spelling slip in the name
    ("Glycomet GP1", "Glycomet GP 1"),
    ("Thyronorm 50 mcg", "Thyronorm 50"),   # unit after the strength
    ("Telma 40mg", "Telma 40"),
])
def test_match_prescription_text_to_brand(brands, text, expected):
    match = brands.match(text)
    assert match is not None and match.brand_name == expected


@pytest.mark.parametrize("text", [
    "Telma 60",          # a strength that doesn't exist must not snap to 40 or 80
    "Glycomet 1000",
    "Paracip 500",       # unknown brand
    "Telma",             # ambiguous: 40 or 80?
])
def test_no_match_when_strength_differs_or_unknown(brands, text):
    assert brands.match(text) is None


# --- prescription lines (plan 9.1) ----------------------------------------------

@pytest.mark.parametrize("line,expected", [
    ("Tab Glycomet 500 1-0-1 x 30 days", RxLine("tab", "Glycomet 500", "BD", "1-0-1", "30 days")),
    ("Tab. Telma 40 OD", RxLine("tab", "Telma 40", "OD", "OD", None)),
    ("Cap Omez 20mg BD before food", RxLine("cap", "Omez 20mg", "BD", "BD", None)),
    ("1. Tab Thyronorm 50 mcg OD empty stomach x 3 months",
     RxLine("tab", "Thyronorm 50 mcg", "OD", "OD", "3 months")),
    ("Tab Dolo 650 SOS", RxLine("tab", "Dolo 650", "SOS", "SOS", None)),
    ("Tab Ecosprin 75 0-1-0", RxLine("tab", "Ecosprin 75", "OD", "0-1-0", None)),
    ("Tab Atorva 10 HS", RxLine("tab", "Atorva 10", "HS", "HS", None)),
    ("TAB ZYLORIC 100 1-1-1 x 2 weeks", RxLine("tab", "ZYLORIC 100", "TDS", "1-1-1", "2 weeks")),
    ("Tab Telma H", RxLine("tab", "Telma H", None, None, None)),
])
def test_parse_prescription_line(line, expected):
    assert parse_prescription_line(line) == expected


@pytest.mark.parametrize("line", [
    "Dr. A Sharma MBBS, MD",
    "Reg. No 12345",
    "Advice: walk daily, avoid sugar",
    "Rx",
    "Tablet should be taken after food",  # "Tablet" in a sentence, not a medicine line
    "",
])
def test_non_medicine_lines(line):
    assert parse_prescription_line(line) is None
