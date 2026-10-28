from decimal import Decimal

import pytest

from app.services.labs.values import (
    compute_flag,
    convert,
    normalize_unit,
    parse_range,
    parse_value,
)


# --- parse_value -------------------------------------------------------------

def test_parse_plain_number():
    assert parse_value("7.2") == (Decimal("7.2"), None)


def test_parse_less_than_qualifier():
    assert parse_value("<0.5") == (Decimal("0.5"), "<")


def test_parse_greater_equal_qualifier_with_space():
    assert parse_value(">= 90") == (Decimal("90"), ">=")


def test_parse_non_numeric_returns_none():
    assert parse_value("Positive") == (None, None)


def test_parse_strips_thousands_separator():
    assert parse_value("1,50,000") == (Decimal("150000"), None)


# --- parse_range -------------------------------------------------------------

def test_range_low_high_hyphen():
    assert parse_range("4.0 - 5.6") == (Decimal("4.0"), Decimal("5.6"))


def test_range_en_dash_no_spaces():
    assert parse_range("0.35–5.50") == (Decimal("0.35"), Decimal("5.50"))


def test_range_upper_limit_only():
    assert parse_range("< 200") == (None, Decimal("200"))


def test_range_lower_limit_only():
    assert parse_range("> 40") == (Decimal("40"), None)


def test_range_missing_or_garbage():
    assert parse_range(None) == (None, None)
    assert parse_range("See note") == (None, None)


# --- normalize_unit ----------------------------------------------------------

@pytest.mark.parametrize("raw", ["uIU/ml", "µIU/mL", "μIU/mL", "microIU/mL", "mIU/L"])
def test_tsh_unit_spellings_collapse(raw):
    assert normalize_unit(raw) == "µIU/mL"


@pytest.mark.parametrize("raw,expected", [
    ("mg/dl", "mg/dL"),
    ("MG/DL", "mg/dL"),
    ("gm/dl", "g/dL"),
    ("g/dl", "g/dL"),
    ("umol/L", "µmol/L"),
    ("%", "%"),
])
def test_common_unit_spellings(raw, expected):
    assert normalize_unit(raw) == expected


def test_unknown_unit_is_kept_trimmed():
    assert normalize_unit("  cells/cumm ") == "cells/cumm"


def test_none_unit():
    assert normalize_unit(None) is None


# --- convert -----------------------------------------------------------------

def test_convert_glucose_mmol_to_mg():
    assert convert(Decimal("5.5"), Decimal("18.016")) == pytest.approx(Decimal("99.088"))


def test_convert_hba1c_ifcc_to_ngsp_uses_offset():
    # Plan 8.3: 53 mmol/mol -> 7.00 %
    result = convert(Decimal("53"), Decimal("0.09152"), Decimal("2.15"))
    assert round(result, 2) == Decimal("7.00")


# --- compute_flag ------------------------------------------------------------

def test_flag_high():
    assert compute_flag(Decimal("7.2"), Decimal("4.0"), Decimal("5.6")) == "high"


def test_flag_low():
    assert compute_flag(Decimal("3.9"), Decimal("4.0"), Decimal("5.6")) == "low"


def test_flag_normal_on_boundary():
    assert compute_flag(Decimal("5.6"), Decimal("4.0"), Decimal("5.6")) == "normal"


def test_flag_upper_limit_only():
    assert compute_flag(Decimal("210"), None, Decimal("200")) == "high"
    assert compute_flag(Decimal("180"), None, Decimal("200")) == "normal"


def test_flag_no_range():
    assert compute_flag(Decimal("7.2"), None, None) == "no_range"


def test_flag_non_numeric():
    assert compute_flag(None, Decimal("4.0"), Decimal("5.6")) == "non_numeric"


def test_flag_less_than_value_below_upper_limit_is_normal():
    # "<0.5" with range "< 1.0" -> normal
    assert compute_flag(Decimal("0.5"), None, Decimal("1.0"), qualifier="<") == "normal"
