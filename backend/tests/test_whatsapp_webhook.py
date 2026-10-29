import hashlib
import hmac
import json

import pytest

from app.core.config import settings
from app.db.models import WhatsAppMessage
from app.main import app
from app.services.queue import get_queue

SECRET = "app-secret"


class FakeQueue:
    def __init__(self):
        self.messages = []

    def enqueue_document(self, document_id):
        pass

    def enqueue_whatsapp(self, message):
        self.messages.append(message)


@pytest.fixture
def wa(client, monkeypatch):
    monkeypatch.setattr(settings, "wa_app_secret", SECRET)
    monkeypatch.setattr(settings, "wa_verify_token", "verify-me")
    q = FakeQueue()
    app.dependency_overrides[get_queue] = lambda: q
    return client, q


def payload(*messages, statuses=None):
    value = {"messaging_product": "whatsapp", "metadata": {"phone_number_id": "PNID"}}
    if messages:
        value["messages"] = list(messages)
    if statuses:
        value["statuses"] = statuses
    return {"object": "whatsapp_business_account", "entry": [{"id": "WABA", "changes": [{"field": "messages",
                                                                                        "value": value}]}]}


def post(client, body, secret=SECRET):
    raw = json.dumps(body).encode()
    sig = "sha256=" + hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    return client.post("/api/v1/whatsapp/webhook", content=raw,
                       headers={"X-Hub-Signature-256": sig, "content-type": "application/json"})


MSG = {"from": "919812345210", "id": "wamid.A", "timestamp": "1793300000", "type": "text", "text": {"body": "hi"}}


def test_verification_handshake(wa):
    client, _ = wa
    ok = client.get("/api/v1/whatsapp/webhook", params={"hub.mode": "subscribe", "hub.verify_token": "verify-me",
                                                        "hub.challenge": "12345"})
    assert (ok.status_code, ok.text) == (200, "12345")
    bad = client.get("/api/v1/whatsapp/webhook", params={"hub.mode": "subscribe", "hub.verify_token": "nope",
                                                         "hub.challenge": "12345"})
    assert bad.status_code == 403


def test_message_is_recorded_without_its_text_and_queued(wa, db_session):
    client, q = wa
    assert post(client, payload(MSG)).status_code == 200
    assert q.messages == [MSG]
    row = db_session.get(WhatsAppMessage, "wamid.A")
    assert (row.phone_e164, row.direction, row.kind, row.status) == ("+919812345210", "in", "text", "received")


def test_retried_delivery_is_queued_once(wa):
    client, q = wa
    post(client, payload(MSG))
    post(client, payload(MSG))
    assert len(q.messages) == 1


def test_bad_or_missing_signature_is_rejected(wa):
    client, q = wa
    assert post(client, payload(MSG), secret="wrong").status_code == 403
    assert client.post("/api/v1/whatsapp/webhook", json=payload(MSG)).status_code == 403
    assert q.messages == []


def test_delivery_statuses_are_ignored(wa):
    client, q = wa
    assert post(client, payload(statuses=[{"id": "wamid.X", "status": "read"}])).status_code == 200
    assert q.messages == []


def test_unconfigured_secret_rejects_everything(client, monkeypatch):
    monkeypatch.setattr(settings, "wa_app_secret", "")
    assert post(client, payload(MSG), secret="").status_code == 403
