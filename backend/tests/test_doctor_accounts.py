import uuid

import pytest
from sqlalchemy import select

from app.db.models import AuditEvent, ProfileMember, User


APPLICATION = {
    "email": "doctor@example.com",
    "password": "correct horse battery",
    "full_name": "Dr. Ananya Mehta",
    "registration_number": "DEMO-12345",
    "registration_council": "Demo Medical Council",
    "specialty": "General medicine",
    "clinic_name": "Demo clinic",
}


def register_doctor(client):
    response = client.post("/api/v1/doctor/register", json=APPLICATION)
    assert response.status_code == 201, response.text
    response = client.post("/api/v1/auth/login", json={k: APPLICATION[k] for k in ("email", "password")})
    assert response.status_code == 200, response.text
    return response.json()


def admin_client(make_user_client, db_session):
    client = make_user_client("admin@example.com")
    user = db_session.scalar(select(User).where(User.email == "admin@example.com"))
    user.account_type = "admin"
    db_session.commit()
    return client, user


def test_doctor_signup_can_login_but_starts_unverified(client):
    user = register_doctor(client)
    assert user["account_type"] == "doctor"
    assert "password_hash" not in user
    profile = client.get("/api/v1/doctor/me")
    assert profile.status_code == 200
    body = profile.json()
    assert body["full_name"] == APPLICATION["full_name"]
    assert body["registration_number"] == "DEMO-12345"
    assert body["verification_status"] == "unverified"
    assert body["verified_by"] is None and body["verified_at"] is None
    assert "password_hash" not in body and "password" not in body
    assert client.get("/api/v1/me").json()["account_type"] == "doctor"


def test_patient_registration_cannot_promote_itself(client):
    body = {"email": "patient@example.com", "password": "correct horse battery", "account_type": "admin"}
    response = client.post("/api/v1/auth/register", json=body)
    assert response.status_code == 201
    assert response.json()["account_type"] == "patient"


@pytest.mark.parametrize("field,value", [
    ("full_name", "   "), ("registration_number", ""), ("registration_council", "\t"),
    ("password", "short"), ("email", "not-an-email"), ("full_name", "x" * 201),
])
def test_invalid_doctor_application_creates_no_account(client, db_session, field, value):
    response = client.post("/api/v1/doctor/register", json={**APPLICATION, field: value})
    assert response.status_code == 422
    assert db_session.scalar(select(User)) is None


@pytest.mark.parametrize("field,value", [("account_type", "admin"), ("verification_status", "verified")])
def test_doctor_signup_rejects_privilege_fields(client, field, value):
    response = client.post("/api/v1/doctor/register", json={**APPLICATION, field: value})
    assert response.status_code == 422


def test_doctor_signup_duplicate_email_is_atomic(client, db_session):
    register_doctor(client)
    response = client.post("/api/v1/doctor/register", json={**APPLICATION, "email": "DOCTOR@EXAMPLE.COM"})
    assert response.status_code == 409
    assert len(db_session.scalars(select(User)).all()) == 1


def test_admin_review_updates_live_doctor_status_and_metadata(client, make_user_client, db_session):
    doctor = register_doctor(client)
    admin, actor = admin_client(make_user_client, db_session)
    listing = admin.get("/api/v1/admin/doctors?status=unverified")
    assert listing.status_code == 200
    assert [d["user_id"] for d in listing.json()] == [doctor["id"]]
    response = admin.post(f'/api/v1/admin/doctors/{doctor["id"]}/verify')
    assert response.status_code == 200
    assert response.json()["verification_status"] == "verified"
    assert response.json()["verified_by"] == str(actor.id)
    assert response.json()["verified_at"] is not None
    assert client.get("/api/v1/doctor/me").json()["verification_status"] == "verified"
    assert admin.get("/api/v1/admin/doctors?status=unverified").json() == []
    response = admin.post(f'/api/v1/admin/doctors/{doctor["id"]}/reject')
    assert response.status_code == 200
    assert response.json()["verification_status"] == "rejected"
    assert response.json()["verified_by"] is None
    assert response.json()["verified_at"] is None
    assert client.get("/api/v1/doctor/me").json()["verification_status"] == "rejected"
    events = db_session.scalars(select(AuditEvent).where(AuditEvent.actor_user_id == actor.id)).all()
    assert {e.action for e in events} == {"doctor.verified", "doctor.rejected"}


def test_only_admin_can_review_doctors(client, make_user_client):
    doctor = register_doctor(client)
    patient = make_user_client("patient@example.com")
    for c in (patient, client):
        assert c.get("/api/v1/admin/doctors").status_code == 403
        for action in ("verify", "reject"):
            assert c.post(f'/api/v1/admin/doctors/{doctor["id"]}/{action}').status_code == 403
    assert patient.get("/api/v1/doctor/me").status_code == 403


def test_doctor_cannot_use_patient_routes_even_with_membership(client, make_user_client, db_session):
    doctor = register_doctor(client)
    patient = make_user_client("patient@example.com")
    pid = patient.post("/api/v1/profiles", json={"display_name": "Papa"}).json()["id"]
    db_session.add(ProfileMember(profile_id=uuid.UUID(pid), user_id=uuid.UUID(doctor["id"]), role="owner"))
    db_session.commit()
    for path in ("/profiles", f"/profiles/{pid}/documents", f"/profiles/{pid}/lab-results",
                 f"/profiles/{pid}/medicines", f"/profiles/{pid}/shares", "/me/whatsapp"):
        assert client.get("/api/v1" + path).status_code == 403, path
    assert client.post("/api/v1/profiles", json={"display_name": "Not allowed"}).status_code == 403
    assert patient.get("/api/v1/profiles").status_code == 200


def test_admin_review_invalid_filter_and_missing_doctor(make_user_client, db_session):
    admin, _ = admin_client(make_user_client, db_session)
    assert admin.get("/api/v1/admin/doctors?status=anything").status_code == 422
    assert admin.post(f"/api/v1/admin/doctors/{uuid.uuid4()}/verify").status_code == 404


def test_doctor_and_admin_routes_require_login(client):
    assert client.get("/api/v1/doctor/me").status_code == 401
    assert client.get("/api/v1/admin/doctors").status_code == 401
