import base64
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.models import AuditEvent, Document, LabResult, LabTestRecord, ShareLink
from app.db.session import get_db
from app.main import app
from app.services.storage import MemoryStorage, get_storage

PAPA = {"display_name": "Papa", "birth_year": 1968}


@pytest.fixture
def storage():
    s = MemoryStorage()
    app.dependency_overrides[get_storage] = lambda: s
    return s


@pytest.fixture
def papa(make_user_client, db_session, storage):
    owner = make_user_client("owner@example.com")
    pid = owner.post("/api/v1/profiles", json=PAPA).json()["id"]
    return owner, pid


@pytest.fixture
def doctor(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    return TestClient(app)  # not logged in


def add_report(db, storage, pid, on, name):
    doc = Document(profile_id=pid, source_channel="web", storage_key=f"docs/{name}", mime_type="application/pdf",
                   size_bytes=3, sha256=name, doc_type="lab_report", report_date=on, status="done", lab_name=name)
    db.add(doc)
    db.flush()
    test_id = db.scalar(select(LabTestRecord.id).where(LabTestRecord.loinc_code == "4548-4"))
    if test_id is None:
        from app.services.labs.dictionary import get_lab_dictionary
        from app.services.labs.store import lab_test_ids
        test_id = lab_test_ids(db, get_lab_dictionary())["4548-4"]
    db.add(LabResult(profile_id=pid, document_id=doc.id, lab_test_id=test_id, raw_name="HbA1c", raw_value="7.2",
                     value_num=Decimal("7.2"), value_canonical=Decimal("7.2"), range_low_canonical=Decimal("4.0"),
                     range_high_canonical=Decimal("5.6"), flag="high", observed_on=on, page_no=1,
                     extraction_method="regex"))
    db.commit()
    storage.put(doc.storage_key, b"PDF", "application/pdf")
    return doc


def share(owner, pid, **body):
    resp = owner.post(f"/api/v1/profiles/{pid}/shares", json={"expires_in": "24h", **body})
    assert resp.status_code == 201, resp.text
    return resp.json()


def token_of(created):
    return created["url"].rsplit("/s/", 1)[1]


def test_create_share_returns_qr_pin_and_link_but_stores_only_hashes(papa, db_session):
    owner, pid = papa
    created = share(owner, pid)

    assert len(created["pin"]) == 4 and created["pin"].isdigit()
    assert created["url"].startswith("http://localhost:5173/s/")
    assert base64.b64decode(created["qr_png_base64"]).startswith(b"\x89PNG")
    link = db_session.get(ShareLink, created["share_id"])
    token = token_of(created)
    assert token not in link.token_hash and created["pin"] not in link.pin_hash
    assert link.snapshot_json["profile"]["display_name"] == "Papa"


def test_doctor_unlocks_with_pin_and_sees_the_frozen_sheet(papa, doctor, db_session, storage):
    owner, pid = papa
    add_report(db_session, storage, pid, date.today() - timedelta(days=30), "Thyrocare")
    created = share(owner, pid)
    token = token_of(created)
    add_report(db_session, storage, pid, date.today() - timedelta(days=1), "Later Lab")  # after sharing

    assert doctor.get(f"/api/v1/s/{token}/sheet").status_code == 401
    assert doctor.post(f"/api/v1/s/{token}/unlock", json={"pin": created["pin"]}).status_code == 200
    sheet = doctor.get(f"/api/v1/s/{token}/sheet").json()

    assert sheet["profile"] == {"display_name": "Papa", "age": date.today().year - 1968, "sex": None}
    assert [r["title"] for r in sheet["reports"]] == ["Thyrocare"]  # frozen: the later report isn't there


def test_doctor_opens_only_documents_in_the_sheet(papa, doctor, db_session, storage):
    owner, pid = papa
    shared = add_report(db_session, storage, pid, date.today() - timedelta(days=30), "Thyrocare")
    old = add_report(db_session, storage, pid, date.today() - timedelta(days=400), "Old Lab")
    created = share(owner, pid)
    token = token_of(created)
    doctor.post(f"/api/v1/s/{token}/unlock", json={"pin": created["pin"]})

    resp = doctor.get(f"/api/v1/s/{token}/documents/{shared.id}")
    assert (resp.status_code, resp.content) == (200, b"PDF")
    assert doctor.get(f"/api/v1/s/{token}/documents/{old.id}").status_code == 404


def test_wrong_pin_five_times_locks_the_link(papa, doctor):
    owner, pid = papa
    created = share(owner, pid)
    token = token_of(created)
    wrong = "0000" if created["pin"] != "0000" else "1111"
    for _ in range(5):
        assert doctor.post(f"/api/v1/s/{token}/unlock", json={"pin": wrong}).status_code == 403
    resp = doctor.post(f"/api/v1/s/{token}/unlock", json={"pin": created["pin"]})
    assert resp.status_code == 423


def test_expired_and_revoked_links_stop_working(papa, doctor, db_session):
    owner, pid = papa
    expired, revoked = share(owner, pid), share(owner, pid)
    link = db_session.get(ShareLink, expired["share_id"])
    link.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db_session.commit()
    assert doctor.post(f"/api/v1/s/{token_of(expired)}/unlock", json={"pin": expired["pin"]}).status_code == 410

    token = token_of(revoked)
    doctor.post(f"/api/v1/s/{token}/unlock", json={"pin": revoked["pin"]})
    assert owner.post(f"/api/v1/shares/{revoked['share_id']}/revoke").status_code == 204
    assert doctor.get(f"/api/v1/s/{token}/sheet").status_code == 410  # even with an unlocked session


def test_unknown_token_is_not_found(doctor):
    assert doctor.post("/api/v1/s/not-a-token/unlock", json={"pin": "1234"}).status_code == 404


def test_session_for_one_link_does_not_open_another(papa, doctor):
    owner, pid = papa
    a, b = share(owner, pid), share(owner, pid)
    doctor.post(f"/api/v1/s/{token_of(a)}/unlock", json={"pin": a["pin"]})
    doctor.cookies.set("share_session", doctor.cookies.get("share_session"), path=f"/api/v1/s/{token_of(b)}")
    assert doctor.get(f"/api/v1/s/{token_of(b)}/sheet").status_code == 401


def test_owner_sees_shares_with_open_counts(papa, doctor, db_session):
    owner, pid = papa
    created = share(owner, pid, expires_in="1h")
    doctor.post(f"/api/v1/s/{token_of(created)}/unlock", json={"pin": created["pin"]})

    [s] = owner.get(f"/api/v1/profiles/{pid}/shares").json()
    assert (s["id"], s["state"], s["opens"]) == (created["share_id"], "active", 1)
    assert s["last_opened_at"]
    actions = db_session.scalars(select(AuditEvent.action).order_by(AuditEvent.id)).all()
    assert actions == ["share.create", "share.open"]


def test_viewers_and_strangers_cannot_share_or_revoke(papa, make_user_client):
    owner, pid = papa
    stranger = make_user_client("x@example.com")
    assert stranger.post(f"/api/v1/profiles/{pid}/shares", json={"expires_in": "1h"}).status_code == 404
    created = share(owner, pid)
    assert stranger.post(f"/api/v1/shares/{created['share_id']}/revoke").status_code == 404


def test_expiry_must_be_one_of_the_offered_choices(papa):
    owner, pid = papa
    assert owner.post(f"/api/v1/profiles/{pid}/shares", json={"expires_in": "30d"}).status_code == 422
