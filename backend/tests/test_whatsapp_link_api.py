import hashlib

from app.db.models import WhatsAppLink, WhatsAppLinkCode


def test_link_code_is_six_digits_and_only_its_hash_is_stored(make_user_client, db_session):
    a = make_user_client("a@example.com")
    body = a.post("/api/v1/me/whatsapp/link-code").json()
    assert len(body["code"]) == 6 and body["code"].isdigit()
    [row] = db_session.query(WhatsAppLinkCode).all()
    assert row.code_hash == hashlib.sha256(body["code"].encode()).hexdigest()


def test_a_new_code_replaces_the_old_unused_one(make_user_client, db_session):
    a = make_user_client("a@example.com")
    a.post("/api/v1/me/whatsapp/link-code")
    a.post("/api/v1/me/whatsapp/link-code")
    assert db_session.query(WhatsAppLinkCode).count() == 1


def test_status_shows_a_masked_phone_and_unlink_removes_it(make_user_client, db_session):
    a = make_user_client("a@example.com")
    assert a.get("/api/v1/me/whatsapp").json() == {"linked": False, "phone": None, "linked_at": None}
    me = a.get("/api/v1/me").json()
    from datetime import datetime, timezone
    import uuid
    db_session.add(WhatsAppLink(user_id=uuid.UUID(me["id"]), phone_e164="+919812345210",
                                linked_at=datetime.now(timezone.utc)))
    db_session.commit()
    status = a.get("/api/v1/me/whatsapp").json()
    assert status["linked"] is True and status["phone"] == "+91 ••••••5210"
    assert a.delete("/api/v1/me/whatsapp").status_code == 204
    assert a.get("/api/v1/me/whatsapp").json()["linked"] is False


def test_needs_login(client):
    assert client.post("/api/v1/me/whatsapp/link-code").status_code == 401
