from datetime import date
from decimal import Decimal

import pytest

from app.db.models import Document, LabResult, ProfileMember, User
from app.services.labs.dictionary import get_lab_dictionary
from app.services.labs.store import lab_test_ids

PAPA = {"display_name": "Papa"}


@pytest.fixture
def test_ids(db_session):
    ids = lab_test_ids(db_session, get_lab_dictionary())
    db_session.commit()
    return ids


def add_doc(db, pid, *, report_date=date(2026, 3, 12), status="done", sha="a"):
    doc = Document(profile_id=pid, source_channel="web", storage_key=f"docs/{sha}", mime_type="application/pdf",
                   size_bytes=1, sha256=sha, doc_type="lab_report", report_date=report_date, status=status)
    db.add(doc)
    db.commit()
    return doc


def add_result(db, doc, loinc, test_ids, *, value="7.2", unit="%", rng="4.0 - 5.6", flag="high",
               observed_on=date(2026, 3, 12), confidence=0.85, name="HbA1c"):
    r = LabResult(profile_id=doc.profile_id, document_id=doc.id, lab_test_id=test_ids.get(loinc), raw_name=name,
                  raw_value=value, raw_unit=unit, raw_range=rng, value_num=Decimal(value),
                  value_canonical=Decimal(value), flag=flag, observed_on=observed_on, page_no=1,
                  bbox={"x0": 1, "y0": 2, "x1": 3, "y1": 4}, extraction_method="regex",
                  extraction_confidence=confidence)
    db.add(r)
    db.commit()
    return r


def test_list_results_for_profile(make_user_client, db_session, test_ids):
    a = make_user_client("a@example.com")
    pid = a.post("/api/v1/profiles", json=PAPA).json()["id"]
    doc = add_doc(db_session, pid)
    add_result(db_session, doc, "4548-4", test_ids)

    [r] = a.get(f"/api/v1/profiles/{pid}/lab-results").json()

    assert r["raw_name"] == "HbA1c"
    assert r["raw_value"] == "7.2"
    assert r["value_canonical"] == 7.2
    assert r["flag"] == "high"
    assert r["observed_on"] == "2026-03-12"
    assert r["test"] == {"loinc_code": "4548-4", "name": "HbA1c", "name_hi": "पिछले 3 महीने की औसत शुगर",
                         "unit": "%", "category": "diabetes"}
    assert r["document_id"] == str(doc.id)
    assert r["bbox"] == {"x0": 1, "y0": 2, "x1": 3, "y1": 4}
    assert r["verified_by_user"] is False


def test_unmapped_result_has_null_test(make_user_client, db_session, test_ids):
    a = make_user_client("a@example.com")
    pid = a.post("/api/v1/profiles", json=PAPA).json()["id"]
    add_result(db_session, add_doc(db_session, pid), "none", test_ids, name="Total Protein")
    [r] = a.get(f"/api/v1/profiles/{pid}/lab-results").json()
    assert r["test"] is None


def test_filter_by_test_name_uses_aliases(make_user_client, db_session, test_ids):
    a = make_user_client("a@example.com")
    pid = a.post("/api/v1/profiles", json=PAPA).json()["id"]
    doc = add_doc(db_session, pid)
    add_result(db_session, doc, "4548-4", test_ids)
    add_result(db_session, doc, "3016-3", test_ids, name="TSH", value="6.81", unit="µIU/mL")

    rows = a.get(f"/api/v1/profiles/{pid}/lab-results", params={"test": "Glycated Haemoglobin"}).json()
    assert [r["raw_name"] for r in rows] == ["HbA1c"]


def test_unknown_test_filter_returns_empty(make_user_client, db_session, test_ids):
    a = make_user_client("a@example.com")
    pid = a.post("/api/v1/profiles", json=PAPA).json()["id"]
    add_result(db_session, add_doc(db_session, pid), "4548-4", test_ids)
    assert a.get(f"/api/v1/profiles/{pid}/lab-results", params={"test": "Unobtainium"}).json() == []


def test_filter_by_date_range_and_newest_first(make_user_client, db_session, test_ids):
    a = make_user_client("a@example.com")
    pid = a.post("/api/v1/profiles", json=PAPA).json()["id"]
    for i, d in enumerate([date(2025, 1, 10), date(2025, 6, 1), date(2026, 3, 12)]):
        doc = add_doc(db_session, pid, report_date=d, sha=str(i))
        add_result(db_session, doc, "4548-4", test_ids, observed_on=d)

    rows = a.get(f"/api/v1/profiles/{pid}/lab-results", params={"from": "2025-02-01", "to": "2026-12-31"}).json()
    assert [r["observed_on"] for r in rows] == ["2026-03-12", "2025-06-01"]


def test_filter_by_document(make_user_client, db_session, test_ids):
    a = make_user_client("a@example.com")
    pid = a.post("/api/v1/profiles", json=PAPA).json()["id"]
    d1, d2 = add_doc(db_session, pid, sha="1"), add_doc(db_session, pid, sha="2")
    add_result(db_session, d1, "4548-4", test_ids)
    add_result(db_session, d2, "3016-3", test_ids, name="TSH")
    rows = a.get(f"/api/v1/profiles/{pid}/lab-results", params={"document_id": str(d2.id)}).json()
    assert [r["raw_name"] for r in rows] == ["TSH"]


def test_other_user_cannot_list_results(make_user_client, db_session, test_ids):
    a = make_user_client("a@example.com")
    b = make_user_client("b@example.com")
    pid = a.post("/api/v1/profiles", json=PAPA).json()["id"]
    add_result(db_session, add_doc(db_session, pid), "4548-4", test_ids)
    assert b.get(f"/api/v1/profiles/{pid}/lab-results").status_code == 404


def test_document_filter_cannot_pull_another_profiles_rows(make_user_client, db_session, test_ids):
    # B owns a profile, and passes A's document id: must get nothing from A
    a = make_user_client("a@example.com")
    b = make_user_client("b@example.com")
    a_pid = a.post("/api/v1/profiles", json=PAPA).json()["id"]
    b_pid = b.post("/api/v1/profiles", json=PAPA).json()["id"]
    a_doc = add_doc(db_session, a_pid)
    add_result(db_session, a_doc, "4548-4", test_ids)
    rows = b.get(f"/api/v1/profiles/{b_pid}/lab-results", params={"document_id": str(a_doc.id)}).json()
    assert rows == []


# --- corrections (plan 3.2: "Please check" screen) -----------------------------

def test_correcting_value_recomputes_and_marks_verified(make_user_client, db_session, test_ids):
    a = make_user_client("a@example.com")
    pid = a.post("/api/v1/profiles", json=PAPA).json()["id"]
    r = add_result(db_session, add_doc(db_session, pid), "4548-4", test_ids, value="72", confidence=0.55)

    resp = a.patch(f"/api/v1/lab-results/{r.id}", json={"raw_value": "7.2"})

    assert resp.status_code == 200
    body = resp.json()
    assert (body["raw_value"], body["value_num"], body["value_canonical"]) == ("7.2", 7.2, 7.2)
    assert body["flag"] == "high"
    assert body["verified_by_user"] is True


def test_correcting_name_remaps_test(make_user_client, db_session, test_ids):
    a = make_user_client("a@example.com")
    pid = a.post("/api/v1/profiles", json=PAPA).json()["id"]
    r = add_result(db_session, add_doc(db_session, pid), "none", test_ids, name="Hb A1 c", value="7.2")

    body = a.patch(f"/api/v1/lab-results/{r.id}", json={"raw_name": "HbA1c"}).json()

    assert body["test"]["loinc_code"] == "4548-4"


def test_correcting_unit_and_range(make_user_client, db_session, test_ids):
    a = make_user_client("a@example.com")
    pid = a.post("/api/v1/profiles", json=PAPA).json()["id"]
    r = add_result(db_session, add_doc(db_session, pid), "1558-6", test_ids, name="Fasting Glucose",
                   value="5.5", unit="mg/dL", rng="70 - 100", flag="low")

    body = a.patch(f"/api/v1/lab-results/{r.id}", json={"raw_unit": "mmol/L", "raw_range": "3.9 - 5.6"}).json()

    assert round(body["value_canonical"], 1) == 99.1
    assert body["flag"] == "normal"


def test_empty_patch_confirms_row(make_user_client, db_session, test_ids):
    a = make_user_client("a@example.com")
    pid = a.post("/api/v1/profiles", json=PAPA).json()["id"]
    r = add_result(db_session, add_doc(db_session, pid), "4548-4", test_ids)
    assert a.patch(f"/api/v1/lab-results/{r.id}", json={}).json()["verified_by_user"] is True


def test_blank_value_rejected(make_user_client, db_session, test_ids):
    a = make_user_client("a@example.com")
    pid = a.post("/api/v1/profiles", json=PAPA).json()["id"]
    r = add_result(db_session, add_doc(db_session, pid), "4548-4", test_ids)
    assert a.patch(f"/api/v1/lab-results/{r.id}", json={"raw_value": "  "}).status_code == 422


def test_fixing_last_doubtful_row_clears_needs_review(make_user_client, db_session, test_ids):
    a = make_user_client("a@example.com")
    pid = a.post("/api/v1/profiles", json=PAPA).json()["id"]
    doc = add_doc(db_session, pid, status="needs_review")
    bad1 = add_result(db_session, doc, "4548-4", test_ids, value="72", confidence=0.55)
    bad2 = add_result(db_session, doc, "3016-3", test_ids, name="TSH", value="681", confidence=0.4)
    add_result(db_session, doc, "2160-0", test_ids, name="Creatinine", value="1.1", confidence=0.85)

    a.patch(f"/api/v1/lab-results/{bad1.id}", json={"raw_value": "7.2"})
    assert a.get(f"/api/v1/documents/{doc.id}").json()["status"] == "needs_review"

    a.patch(f"/api/v1/lab-results/{bad2.id}", json={"raw_value": "6.81"})
    assert a.get(f"/api/v1/documents/{doc.id}").json()["status"] == "done"


def test_setting_report_date_updates_rows_and_clears_review(make_user_client, db_session, test_ids):
    a = make_user_client("a@example.com")
    pid = a.post("/api/v1/profiles", json=PAPA).json()["id"]
    doc = add_doc(db_session, pid, report_date=None, status="needs_review")
    add_result(db_session, doc, "4548-4", test_ids, observed_on=date(2026, 10, 28))

    resp = a.patch(f"/api/v1/documents/{doc.id}", json={"report_date": "2026-03-12"})

    assert resp.status_code == 200
    assert (resp.json()["report_date"], resp.json()["status"]) == ("2026-03-12", "done")
    [r] = a.get(f"/api/v1/profiles/{pid}/lab-results").json()
    assert r["observed_on"] == "2026-03-12"


def test_report_date_in_future_rejected(make_user_client, db_session, test_ids):
    a = make_user_client("a@example.com")
    pid = a.post("/api/v1/profiles", json=PAPA).json()["id"]
    doc = add_doc(db_session, pid)
    assert a.patch(f"/api/v1/documents/{doc.id}", json={"report_date": "2999-01-01"}).status_code == 422


def test_failed_document_status_not_changed_by_review(make_user_client, db_session, test_ids):
    a = make_user_client("a@example.com")
    pid = a.post("/api/v1/profiles", json=PAPA).json()["id"]
    doc = add_doc(db_session, pid, status="failed")
    a.patch(f"/api/v1/documents/{doc.id}", json={"report_date": "2026-03-12"})
    assert a.get(f"/api/v1/documents/{doc.id}").json()["status"] == "failed"


def test_other_user_cannot_correct(make_user_client, db_session, test_ids):
    a = make_user_client("a@example.com")
    b = make_user_client("b@example.com")
    pid = a.post("/api/v1/profiles", json=PAPA).json()["id"]
    doc = add_doc(db_session, pid)
    r = add_result(db_session, doc, "4548-4", test_ids)
    assert b.patch(f"/api/v1/lab-results/{r.id}", json={"raw_value": "5.0"}).status_code == 404
    assert b.patch(f"/api/v1/documents/{doc.id}", json={"report_date": "2026-01-01"}).status_code == 404


def test_viewer_cannot_correct(make_user_client, db_session, test_ids):
    a = make_user_client("a@example.com")
    v = make_user_client("v@example.com")
    pid = a.post("/api/v1/profiles", json=PAPA).json()["id"]
    r = add_result(db_session, add_doc(db_session, pid), "4548-4", test_ids)
    v_user = db_session.query(User).filter_by(email="v@example.com").one()
    db_session.add(ProfileMember(profile_id=pid, user_id=v_user.id, role="viewer"))
    db_session.commit()
    assert v.patch(f"/api/v1/lab-results/{r.id}", json={"raw_value": "5.0"}).status_code == 403
