from datetime import date
from decimal import Decimal

import pytest

from app.db.models import Document, LabResult
from app.services.labs.dictionary import get_lab_dictionary
from app.services.labs.store import lab_test_ids

PAPA = {"display_name": "Papa"}


@pytest.fixture
def test_ids(db_session):
    ids = lab_test_ids(db_session, get_lab_dictionary())
    db_session.commit()
    return ids


def add_point(db, pid, test_ids, loinc, value, on, *, low="4.0", high="5.6", flag="high", confidence=0.85,
              verified=False, canonical=True):
    doc = Document(profile_id=pid, source_channel="web", storage_key=f"docs/{loinc}{on}", mime_type="application/pdf",
                   size_bytes=1, sha256=f"{loinc}{on}{value}", doc_type="lab_report", report_date=on, status="done")
    db.add(doc)
    db.flush()
    r = LabResult(profile_id=pid, document_id=doc.id, lab_test_id=test_ids.get(loinc), raw_name=loinc,
                  raw_value=value, value_num=Decimal(value), value_canonical=Decimal(value) if canonical else None,
                  range_low_canonical=Decimal(low) if low else None, range_high_canonical=Decimal(high) if high else None,
                  flag=flag, observed_on=on, page_no=2, extraction_method="regex",
                  extraction_confidence=confidence, verified_by_user=verified)
    db.add(r)
    db.commit()
    return r


def test_trend_has_points_oldest_first_with_ranges_and_sources(make_user_client, db_session, test_ids):
    a = make_user_client("a@example.com")
    pid = a.post("/api/v1/profiles", json=PAPA).json()["id"]
    later = add_point(db_session, pid, test_ids, "4548-4", "7.2", date(2026, 6, 14))
    add_point(db_session, pid, test_ids, "4548-4", "8.1", date(2026, 1, 10))

    [trend] = a.get(f"/api/v1/profiles/{pid}/trends").json()

    assert trend["test"]["name"] == "HbA1c"
    assert trend["test"]["unit"] == "%"
    assert [p["value"] for p in trend["points"]] == [8.1, 7.2]
    last = trend["points"][-1]
    assert last["observed_on"] == "2026-06-14"
    assert (last["range_low"], last["range_high"], last["flag"]) == (4.0, 5.6, "high")
    assert (last["lab_result_id"], last["document_id"], last["page_no"]) == (str(later.id), str(later.document_id), 2)
    assert last["low_confidence"] is False
    assert trend["latest"] == last


def test_tests_with_one_point_are_left_out(make_user_client, db_session, test_ids):
    a = make_user_client("a@example.com")
    pid = a.post("/api/v1/profiles", json=PAPA).json()["id"]
    add_point(db_session, pid, test_ids, "4548-4", "7.2", date(2026, 6, 14))
    add_point(db_session, pid, test_ids, "4548-4", "8.1", date(2026, 1, 10))
    add_point(db_session, pid, test_ids, "3016-3", "6.81", date(2026, 6, 14))
    assert [t["test"]["name"] for t in a.get(f"/api/v1/profiles/{pid}/trends").json()] == ["HbA1c"]


def test_unmapped_and_unconverted_rows_are_not_plotted(make_user_client, db_session, test_ids):
    a = make_user_client("a@example.com")
    pid = a.post("/api/v1/profiles", json=PAPA).json()["id"]
    add_point(db_session, pid, test_ids, "4548-4", "7.2", date(2026, 6, 14))
    add_point(db_session, pid, test_ids, "4548-4", "8.1", date(2026, 1, 10), canonical=False)  # unknown unit
    add_point(db_session, pid, test_ids, "unmapped", "7.0", date(2026, 1, 1))
    add_point(db_session, pid, test_ids, "unmapped", "7.1", date(2026, 2, 1))
    assert a.get(f"/api/v1/profiles/{pid}/trends").json() == []


def test_missing_range_point_says_no_range(make_user_client, db_session, test_ids):
    a = make_user_client("a@example.com")
    pid = a.post("/api/v1/profiles", json=PAPA).json()["id"]
    add_point(db_session, pid, test_ids, "4548-4", "7.2", date(2026, 6, 14), low=None, high=None, flag="no_range")
    add_point(db_session, pid, test_ids, "4548-4", "8.1", date(2026, 1, 10))
    last = a.get(f"/api/v1/profiles/{pid}/trends").json()[0]["latest"]
    assert (last["range_low"], last["range_high"], last["flag"]) == (None, None, "no_range")


def test_unreviewed_low_confidence_point_is_marked(make_user_client, db_session, test_ids):
    a = make_user_client("a@example.com")
    pid = a.post("/api/v1/profiles", json=PAPA).json()["id"]
    add_point(db_session, pid, test_ids, "4548-4", "7.2", date(2026, 6, 14), confidence=0.4)
    add_point(db_session, pid, test_ids, "4548-4", "8.1", date(2026, 1, 10), confidence=0.4, verified=True)
    points = a.get(f"/api/v1/profiles/{pid}/trends").json()[0]["points"]
    assert [p["low_confidence"] for p in points] == [False, True]


def test_trends_sorted_by_category_then_name(make_user_client, db_session, test_ids):
    a = make_user_client("a@example.com")
    pid = a.post("/api/v1/profiles", json=PAPA).json()["id"]
    for loinc, v in [("3016-3", "6.8"), ("4548-4", "7.2"), ("1558-6", "99")]:
        add_point(db_session, pid, test_ids, loinc, v, date(2026, 1, 10))
        add_point(db_session, pid, test_ids, loinc, v, date(2026, 6, 14))
    names = [t["test"]["name"] for t in a.get(f"/api/v1/profiles/{pid}/trends").json()]
    assert names == ["Fasting glucose", "HbA1c", "TSH"]


def test_other_user_cannot_see_trends(make_user_client, db_session, test_ids):
    a = make_user_client("a@example.com")
    b = make_user_client("b@example.com")
    pid = a.post("/api/v1/profiles", json=PAPA).json()["id"]
    assert b.get(f"/api/v1/profiles/{pid}/trends").status_code == 404


def test_trends_never_mix_profiles(make_user_client, db_session, test_ids):
    a = make_user_client("a@example.com")
    papa = a.post("/api/v1/profiles", json=PAPA).json()["id"]
    mummy = a.post("/api/v1/profiles", json={"display_name": "Mummy"}).json()["id"]
    add_point(db_session, papa, test_ids, "4548-4", "7.2", date(2026, 6, 14))
    add_point(db_session, mummy, test_ids, "4548-4", "5.1", date(2026, 1, 10))
    assert a.get(f"/api/v1/profiles/{papa}/trends").json() == []


def test_converted_values_are_rounded_and_printed_ones_kept(make_user_client, db_session, test_ids):
    # Found in the browser: "118.9056 mg/dL" for a glucose printed as 6.6 mmol/L.
    a = make_user_client("a@example.com")
    pid = a.post("/api/v1/profiles", json=PAPA).json()["id"]
    converted = add_point(db_session, pid, test_ids, "1558-6", "6.6", date(2026, 1, 10), low="70.2624", high="99.0880")
    converted.value_canonical, converted.range_low, converted.range_high = Decimal("118.9056"), Decimal("3.9"), Decimal("5.5")
    add_point(db_session, pid, test_ids, "1558-6", "104.25", date(2026, 6, 14), low="70", high="100")
    db_session.commit()

    [trend] = a.get(f"/api/v1/profiles/{pid}/trends").json()

    first, last = trend["points"]
    assert (first["value"], first["range_low"], first["range_high"]) == (119, 70.3, 99.1)
    assert (last["value"], last["range_low"], last["range_high"]) == (104.25, 70, 100)  # as printed: not rounded
