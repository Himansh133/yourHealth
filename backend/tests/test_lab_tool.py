from datetime import date
from decimal import Decimal

import pytest

from app.db.models import Document, LabResult
from app.services.chat.lab_tool import lab_lookup
from app.services.labs.dictionary import get_lab_dictionary
from app.services.labs.store import lab_test_ids

PAPA = {"display_name": "Papa"}


@pytest.fixture
def test_ids(db_session):
    ids = lab_test_ids(db_session, get_lab_dictionary())
    db_session.commit()
    return ids


@pytest.fixture
def pid(make_user_client):
    return make_user_client("a@example.com").post("/api/v1/profiles", json=PAPA).json()["id"]


def add(db, pid, test_ids, loinc, value, on, *, low="4.0", high="5.6", flag="high", lab="Dr Lal PathLabs",
        canonical=True, raw_unit="%"):
    doc = Document(profile_id=pid, source_channel="web", storage_key=f"docs/{loinc}{on}", mime_type="application/pdf",
                   size_bytes=1, sha256=f"{loinc}{on}{value}", doc_type="lab_report", report_date=on, status="done",
                   lab_name=lab)
    db.add(doc)
    db.flush()
    r = LabResult(profile_id=pid, document_id=doc.id, lab_test_id=test_ids.get(loinc), raw_name=loinc,
                  raw_value=value, raw_unit=raw_unit, value_num=Decimal(value),
                  value_canonical=Decimal(value) if canonical else None,
                  range_low_canonical=Decimal(low) if low else None, range_high_canonical=Decimal(high) if high else None,
                  flag=flag, observed_on=on, page_no=2, extraction_method="regex")
    db.add(r)
    db.commit()
    return r


def test_latest_returns_most_recent_row_with_citation_ids(db_session, test_ids, pid):
    add(db_session, pid, test_ids, "4548-4", "8.1", date(2026, 1, 10))
    june = add(db_session, pid, test_ids, "4548-4", "7.2", date(2026, 6, 14))

    [fact] = lab_lookup(db_session, pid, "4548-4", "latest")

    assert (fact.lab_result_id, fact.document_id, fact.page_no) == (june.id, june.document_id, 2)
    assert fact.evidence_text() == "lab_result | HbA1c 7.2 % (ref 4.0-5.6) HIGH | 2026-06-14 | Dr Lal PathLabs p.2"


def test_trend_returns_all_rows_oldest_first(db_session, test_ids, pid):
    add(db_session, pid, test_ids, "4548-4", "7.2", date(2026, 6, 14))
    add(db_session, pid, test_ids, "4548-4", "8.1", date(2026, 1, 10))
    facts = lab_lookup(db_session, pid, "4548-4", "trend")
    assert [f.observed_on for f in facts] == [date(2026, 1, 10), date(2026, 6, 14)]


def test_date_window_filters_rows(db_session, test_ids, pid):
    add(db_session, pid, test_ids, "4548-4", "8.1", date(2025, 11, 1))
    add(db_session, pid, test_ids, "4548-4", "7.2", date(2026, 6, 14))
    facts = lab_lookup(db_session, pid, "4548-4", "range", date_from=date(2026, 1, 1))
    assert [f.observed_on for f in facts] == [date(2026, 6, 14)]


def test_known_test_with_no_rows_returns_empty_list(db_session, test_ids, pid):
    assert lab_lookup(db_session, pid, "4548-4", "latest") == []


def test_other_profiles_rows_are_never_returned(db_session, test_ids, pid, make_user_client):
    other = make_user_client("b@example.com").post("/api/v1/profiles", json=PAPA).json()["id"]
    add(db_session, other, test_ids, "4548-4", "9.9", date(2026, 6, 14))
    assert lab_lookup(db_session, pid, "4548-4", "trend") == []


def test_unconverted_value_is_shown_as_printed_and_missing_range_said(db_session, test_ids, pid):
    add(db_session, pid, test_ids, "4548-4", "53", date(2026, 6, 14), canonical=False, raw_unit="mmol/mol",
        low=None, high=None, flag="no_range", lab=None)
    [fact] = lab_lookup(db_session, pid, "4548-4", "latest")
    assert fact.evidence_text() == "lab_result | HbA1c 53 mmol/mol (no range printed) | 2026-06-14 | p.2"
