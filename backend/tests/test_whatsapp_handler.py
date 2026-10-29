import json
import uuid
from datetime import datetime, timedelta, timezone

import pymupdf
import pytest

from app.db.models import Document, User, WhatsAppLink, WhatsAppLinkCode, WhatsAppPendingUpload
from app.services.chat.llm import FakeLLM, LLMError
from app.services.storage import MemoryStorage
from app.services.whatsapp.handler import handle_message, hash_code, report_done_message

PHONE = "+919812345210"


class FakeWhatsApp:
    def __init__(self, media=None):
        self.sent = []
        self.media = media or {}

    def send_text(self, to, body):
        self.sent.append(("text", to, body))

    def send_buttons(self, to, body, buttons):
        self.sent.append(("buttons", to, body, buttons))

    def send_list(self, to, body, button, rows):
        self.sent.append(("list", to, body, rows))

    def download_media(self, media_id):
        return self.media[media_id]


class FakeQueue:
    def __init__(self):
        self.documents = []

    def enqueue_document(self, document_id):
        self.documents.append(document_id)


def pdf() -> bytes:
    doc = pymupdf.open()
    doc.new_page().insert_text((40, 60), "HbA1c 7.2 % 4.0 - 5.6", fontsize=9)
    return doc.tobytes()


def text(body, mid="wamid.1"):
    return {"from": PHONE.lstrip("+"), "id": mid, "type": "text", "text": {"body": body}}


@pytest.fixture
def family(make_user_client, db_session):
    """A user with Papa and Mummy, and their phone linked."""
    a = make_user_client("a@example.com")
    papa = a.post("/api/v1/profiles", json={"display_name": "Papa"}).json()["id"]
    mummy = a.post("/api/v1/profiles", json={"display_name": "Mummy"}).json()["id"]
    user = db_session.query(User).one()
    db_session.add(WhatsAppLink(user_id=user.id, phone_e164=PHONE, linked_at=datetime.now(timezone.utc)))
    db_session.commit()
    return {"client": a, "user": user, "papa": uuid.UUID(papa), "mummy": uuid.UUID(mummy)}


class DownLLM:
    """Behaves like an unreachable provider: questions fall back without an LLM answer."""

    def complete_json(self, system, user):
        raise LLMError("down")


def run(db, msg, wa=None, llm=None, queue=None, storage=None):
    wa = wa or FakeWhatsApp()
    handle_message(db, wa, storage or MemoryStorage(), queue or FakeQueue(), llm or DownLLM(), msg)
    return wa


# --- linking -------------------------------------------------------------------------------------------------

def test_link_with_a_valid_code(make_user_client, db_session):
    make_user_client("a@example.com")
    user = db_session.query(User).one()
    db_session.add(WhatsAppLinkCode(code_hash=hash_code("482913"), user_id=user.id,
                                    expires_at=datetime.now(timezone.utc) + timedelta(minutes=5)))
    db_session.commit()

    wa = run(db_session, text("LINK 482913"))

    link = db_session.query(WhatsAppLink).one()
    assert (link.user_id, link.phone_e164) == (user.id, PHONE)
    assert "Connected" in wa.sent[0][2]
    assert db_session.query(WhatsAppLinkCode).one().used_at is not None


@pytest.mark.parametrize("expires, used", [(-1, False), (5, True)])
def test_expired_or_used_code_does_not_link(make_user_client, db_session, expires, used):
    make_user_client("a@example.com")
    user = db_session.query(User).one()
    now = datetime.now(timezone.utc)
    db_session.add(WhatsAppLinkCode(code_hash=hash_code("482913"), user_id=user.id,
                                    expires_at=now + timedelta(minutes=expires), used_at=now if used else None))
    db_session.commit()
    wa = run(db_session, text("link 482913"))
    assert db_session.query(WhatsAppLink).count() == 0
    assert "didn't work" in wa.sent[0][2]


def test_unlinked_phone_is_told_how_to_link(db_session):
    wa = run(db_session, text("papa ka sugar?"))
    assert "Connect WhatsApp" in wa.sent[0][2]


# --- reports ---------------------------------------------------------------------------------------------------

def doc_msg(mid="wamid.2", media="MEDIA1"):
    return {"from": PHONE.lstrip("+"), "id": mid, "type": "document",
            "document": {"id": media, "mime_type": "application/pdf", "filename": "report.pdf"}}


def test_file_asks_whose_report_with_a_button_per_profile(family, db_session):
    wa = run(db_session, doc_msg())
    [(kind, to, body, buttons)] = wa.sent
    pending = db_session.query(WhatsAppPendingUpload).one()
    assert (kind, to, body) == ("buttons", PHONE, "Whose report is this?")
    assert buttons == [(f"up:{pending.id}:{family['papa']}", "Papa"), (f"up:{pending.id}:{family['mummy']}", "Mummy")]


def test_more_than_three_profiles_get_a_list(family, db_session):
    for name in ("Dadi", "Nana"):
        family["client"].post("/api/v1/profiles", json={"display_name": name})
    wa = run(db_session, doc_msg())
    assert wa.sent[0][0] == "list" and len(wa.sent[0][3]) == 4


def tap(button_id, mid="wamid.3"):
    return {"from": PHONE.lstrip("+"), "id": mid, "type": "interactive",
            "interactive": {"type": "button_reply", "button_reply": {"id": button_id, "title": "Papa"}}}


def test_tapping_a_profile_downloads_stores_and_queues_the_report(family, db_session):
    run(db_session, doc_msg())
    pending = db_session.query(WhatsAppPendingUpload).one()
    wa, queue = FakeWhatsApp(media={"MEDIA1": (pdf(), "application/pdf")}), FakeQueue()

    run(db_session, tap(f"up:{pending.id}:{family['papa']}"), wa=wa, queue=queue)

    doc = db_session.query(Document).one()
    assert (doc.profile_id, doc.source_channel, doc.uploaded_by) == (family["papa"], "whatsapp", family["user"].id)
    assert queue.documents == [doc.id]
    assert wa.sent[0][2] == "Got it. Reading Papa's report…"
    assert db_session.query(WhatsAppPendingUpload).count() == 0


def test_expired_pending_upload_asks_to_send_again(family, db_session):
    run(db_session, doc_msg())
    pending = db_session.query(WhatsAppPendingUpload).one()
    pending.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db_session.commit()
    wa = run(db_session, tap(f"up:{pending.id}:{family['papa']}"))
    assert "send it again" in wa.sent[0][2]
    assert db_session.query(Document).count() == 0


def test_someone_elses_pending_upload_or_profile_is_refused(family, db_session, make_user_client):
    other = make_user_client("b@example.com").post("/api/v1/profiles", json={"display_name": "X"}).json()["id"]
    run(db_session, doc_msg())
    pending = db_session.query(WhatsAppPendingUpload).one()
    wa = run(db_session, tap(f"up:{pending.id}:{other}"), wa=FakeWhatsApp(media={"MEDIA1": (pdf(), "application/pdf")}))
    assert db_session.query(Document).count() == 0
    assert "send it again" in wa.sent[0][2]


def test_unreadable_file_is_refused_with_the_reason(family, db_session):
    run(db_session, doc_msg())
    pending = db_session.query(WhatsAppPendingUpload).one()
    wa = run(db_session, tap(f"up:{pending.id}:{family['papa']}"),
             wa=FakeWhatsApp(media={"MEDIA1": (b"not a pdf", "application/pdf")}))
    assert db_session.query(Document).count() == 0
    assert wa.sent[0][2].startswith("I couldn't take this file")


# --- questions -------------------------------------------------------------------------------------------------

def test_question_naming_a_profile_is_answered_for_them_with_a_link(family, db_session):
    llm = FakeLLM([])  # no values yet: answered without the LLM
    wa = run(db_session, text("What was papa's last HbA1c?"), llm=llm)
    body = wa.sent[0][2]
    assert body.startswith("Answering for Papa.")
    assert "I couldn't find this in Papa's reports." in body
    assert f"/profiles/{family['papa']}/ask" in body
    assert db_session.query(WhatsAppLink).one().last_profile_id == family["papa"]


def test_hindi_name_and_hinglish_question(family, db_session):
    wa = run(db_session, text("मम्मी का पिछला HbA1c कितना था?"))
    assert wa.sent[0][2].startswith("Answering for Mummy.")


def test_without_a_name_the_last_profile_is_used(family, db_session):
    run(db_session, text("papa ka hba1c?"))
    wa = run(db_session, text("and the latest TSH?", mid="wamid.9"))
    assert wa.sent[0][2].startswith("Answering for Papa.")


def test_without_a_name_or_history_it_asks_whom_the_question_is_about(family, db_session):
    wa = run(db_session, text("latest HbA1c?"))
    kind, _, body, buttons = wa.sent[0]
    assert kind == "buttons" and "Who is this question about?" in body
    assert buttons[0] == (f"ask:{family['papa']}", "Papa")


def test_switch_then_tap_sets_the_profile(family, db_session):
    run(db_session, text("papa ka hba1c?"))
    wa = run(db_session, text("switch", mid="wamid.5"))
    assert wa.sent[0][0] == "buttons"
    wa = run(db_session, tap(f"ask:{family['mummy']}", mid="wamid.6"))
    assert "Mummy" in wa.sent[0][2]
    assert db_session.query(WhatsAppLink).one().last_profile_id == family["mummy"]


def test_other_message_types_get_help(family, db_session):
    wa = run(db_session, {"from": PHONE.lstrip("+"), "id": "wamid.7", "type": "audio", "audio": {"id": "A"}})
    assert "PDFs and photos" in wa.sent[0][2]


# --- after processing --------------------------------------------------------------------------------------------

def test_done_message_counts_tests_and_names_flagged_values(family, db_session):
    from decimal import Decimal

    from app.db.models import LabResult
    from app.services.labs.dictionary import get_lab_dictionary
    from app.services.labs.store import lab_test_ids
    ids = lab_test_ids(db_session, get_lab_dictionary())
    doc = Document(profile_id=family["papa"], source_channel="whatsapp", storage_key="k", mime_type="application/pdf",
                   size_bytes=1, sha256="s", status="done", doc_type="lab_report", uploaded_by=family["user"].id)
    db_session.add(doc)
    db_session.flush()
    for loinc, v, flag in [("4548-4", "7.2", "high"), ("2160-0", "1.0", "normal")]:
        db_session.add(LabResult(profile_id=family["papa"], document_id=doc.id, lab_test_id=ids[loinc], raw_name=loinc,
                                 raw_value=v, raw_unit="%", value_num=Decimal(v), value_canonical=Decimal(v), flag=flag,
                                 observed_on=datetime(2026, 6, 14).date(), extraction_method="regex"))
    db_session.commit()
    msg = report_done_message(db_session, doc)
    assert msg.startswith("Done. Papa's report: 2 tests found. Outside the report's range: HbA1c 7.2 % (high).")
    assert f"/documents/{doc.id}/review" in msg


def test_done_notification_goes_only_to_the_whatsapp_sender(family, db_session):
    from app.services.whatsapp.handler import notify_report_done
    docs = {}
    for channel in ("whatsapp", "web"):
        d = Document(profile_id=family["papa"], source_channel=channel, storage_key=channel, mime_type="application/pdf",
                     size_bytes=1, sha256=channel, status="failed", uploaded_by=family["user"].id)
        db_session.add(d)
        docs[channel] = d
    db_session.commit()
    wa = FakeWhatsApp()
    notify_report_done(db_session, wa, docs["whatsapp"].id)
    notify_report_done(db_session, wa, docs["web"].id)
    [(_, to, body)] = wa.sent
    assert to == PHONE and body.startswith("Sorry, I couldn't read Papa's file")


def test_profiles_with_the_same_name_get_numbered_buttons(family, db_session):
    family["client"].post("/api/v1/profiles", json={"display_name": "Papa"})
    wa = run(db_session, doc_msg())
    assert [title for _, title in wa.sent[0][3]] == ["Papa", "Mummy", "Papa (2)"]


def test_sending_a_report_makes_that_profile_the_one_questions_are_about(family, db_session):
    run(db_session, doc_msg())
    pending = db_session.query(WhatsAppPendingUpload).one()
    run(db_session, tap(f"up:{pending.id}:{family['mummy']}"), wa=FakeWhatsApp(media={"MEDIA1": (pdf(), "application/pdf")}))
    wa = run(db_session, text("latest HbA1c?", mid="wamid.8"))
    assert wa.sent[0][2].startswith("Answering for Mummy.")


def test_a_name_shared_by_two_profiles_prefers_the_one_last_used(family, db_session):
    second = uuid.UUID(family["client"].post("/api/v1/profiles", json={"display_name": "Papa"}).json()["id"])
    link = db_session.query(WhatsAppLink).one()
    link.last_profile_id = second
    db_session.commit()
    wa = run(db_session, text("papa ka hba1c?"))
    assert f"/profiles/{second}/ask" in wa.sent[0][2]
