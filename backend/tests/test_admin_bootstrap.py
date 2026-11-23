import pytest
from sqlalchemy import select

from app.admin import create_admin
from app.core.security import verify_password
from app.db.models import User


def test_create_admin_can_login(client, db_session):
    user = create_admin(db_session, "admin@example.com", "a long admin password")
    assert user.account_type == "admin"
    assert verify_password("a long admin password", user.password_hash)
    response = client.post("/api/v1/auth/login", json={"email": user.email, "password": "a long admin password"})
    assert response.status_code == 200
    assert client.get("/api/v1/admin/doctors").status_code == 200


def test_existing_patient_is_never_promoted(client, db_session):
    client.post("/api/v1/auth/register", json={"email": "patient@example.com", "password": "a patient password"})
    with pytest.raises(ValueError, match="already registered"):
        create_admin(db_session, "PATIENT@example.com", "a long admin password")
    user = db_session.scalar(select(User).where(User.email == "patient@example.com"))
    assert user.account_type == "patient"
    assert verify_password("a patient password", user.password_hash)


def test_invalid_admin_credentials_create_nothing(db_session):
    with pytest.raises(ValueError):
        create_admin(db_session, "invalid-email", "short")
    assert db_session.scalar(select(User)) is None
