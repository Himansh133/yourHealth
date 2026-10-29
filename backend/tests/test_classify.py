from datetime import date

import pytest

from app.services.extraction.classify import classify_document, find_lab_name, find_report_date


# --- report date ---------------------------------------------------------------

@pytest.mark.parametrize("text,expected", [
    ("Sample Collected: 12/03/2026 09:15 AM", date(2026, 3, 12)),
    ("Collected On : 12-03-2026", date(2026, 3, 12)),
    ("Sample Collection Date 05.11.2025", date(2025, 11, 5)),
    ("Collected: 12/03/26", date(2026, 3, 12)),
    ("Collected : 12-Mar-2026 10:02", date(2026, 3, 12)),
    ("Collection Date: 3 March 2026", date(2026, 3, 3)),
    ("Reported : 2026-03-14", date(2026, 3, 14)),
])
def test_finds_date_after_label(text, expected):
    assert find_report_date(text) == expected


def test_prefers_collection_over_reported_and_registered():
    text = "Registered: 10/03/2026\nReported: 14/03/2026\nSample Collected: 12/03/2026"
    assert find_report_date(text) == date(2026, 3, 12)


def test_falls_back_to_reported_date():
    assert find_report_date("Registered: 10/03/2026\nReported: 14/03/2026") == date(2026, 3, 14)


def test_day_first_not_month_first():
    assert find_report_date("Collected: 04/05/2026") == date(2026, 5, 4)


def test_ignores_dates_without_a_label():
    # e.g. a date of birth must never become the report date
    assert find_report_date("DOB: 01/01/1968\nPrinted 12/03/2026") is None


def test_impossible_date_is_ignored():
    assert find_report_date("Collected: 31/02/2026") is None


# --- lab name --------------------------------------------------------------------

def test_known_lab_chain_found_case_insensitive():
    assert find_lab_name("DR LAL PATHLABS LTD\nNational Reference Lab") == "Dr Lal PathLabs"
    assert find_lab_name("Thyrocare Technologies") == "Thyrocare"


def test_unknown_lab_is_none():
    assert find_lab_name("Demo Diagnostics Centre") is None


# --- document type ---------------------------------------------------------------

def test_lab_report_needs_keyword_and_three_rows():
    assert classify_document("Test Name Result Units Reference Range", lab_row_count=3) == "lab_report"


def test_rows_without_lab_keywords_are_not_a_lab_report():
    assert classify_document("Random table", lab_row_count=5) == "other"


def test_few_rows_are_not_a_lab_report():
    assert classify_document("Reference Range", lab_row_count=2) == "other"


def test_prescription():
    text = "Dr. A Sharma MBBS Reg. No 12345\nRx\nTab Glycomet 500 1-0-1 x 30 days\nTab Telma 40 OD"
    assert classify_document(text, lab_row_count=0) == "prescription"


def test_other():
    assert classify_document("Invoice total Rs 500", lab_row_count=0) == "other"


def test_discharge_summary_is_detected_even_with_medicine_lines():
    text = ("City Care Hospital\nDISCHARGE SUMMARY\nDiagnosis: Type 2 diabetes\n"
            "Medications on discharge:\nTab Glycomet 500 BD\nTab Ecosprin 75 OD")
    assert classify_document(text, 0) == "discharge"


def test_word_discharge_alone_is_not_enough():
    assert classify_document("Tab Pan 40 OD\nRx\nNo discharge from wound", 0) == "prescription"


def test_discharge_summary_uses_the_discharge_date_over_admission():
    text = "DISCHARGE SUMMARY\nDate of Admission: 25/02/2026\nDate of Discharge: 02/03/2026\nDiagnosis: diabetes"
    assert find_report_date(text) == date(2026, 3, 2)


def test_admission_date_when_no_discharge_date():
    assert find_report_date("Admitted on 25 Feb 2026\nDiagnosis: diabetes") == date(2026, 2, 25)
