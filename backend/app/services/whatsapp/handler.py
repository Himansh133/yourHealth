"""What the bot does with one incoming WhatsApp message (plan 3.3, 7.4). Runs in the worker, not the webhook.

Privacy rule for replies: short summaries and a link to the app, never whole reports.
"""
import hashlib
import re
import uuid
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.permissions import _ALLOWED
from app.db.models import (
    AuditEvent,
    Document,
    LabResult,
    LabTestRecord,
    Profile,
    ProfileMember,
    User,
    WhatsAppLink,
    WhatsAppLinkCode,
    WhatsAppPendingUpload,
)
from app.services.chat.llm import LLM
from app.services.audit import record
from app.services.chat.service import answer_chat
from app.services.extraction.validate import UploadRejected
from app.services.queue import DocumentQueue
from app.services.storage import Storage
from app.services.uploads import store_upload
from app.services.whatsapp.client import MAX_BUTTONS, WhatsApp

PENDING_MINUTES = 30
# A 6-digit code could be guessed by brute force: after this many wrong codes a phone waits an hour (plan 7.4).
MAX_LINK_FAILURES_PER_HOUR = 5
MAX_CLAIMS_IN_REPLY = 3
LINK_RE = re.compile(r"^link\s+(\d{6})$", re.IGNORECASE)
DEVANAGARI = re.compile(r"[ऀ-ॿ]")
HINGLISH = re.compile(r"\b(ka|ki|ke|hai|hain|kya|kaisa|kaisi|kitna|kitni|tha|thi|mein|ko|kab|batao)\b", re.IGNORECASE)
# How people name family members in Hindi, for matching a question to a profile
HINDI_NAMES = {"papa": ["पापा", "पिताजी", "pitaji"], "mummy": ["मम्मी", "माँ", "मां", "maa", "mom"],
               "dadi": ["दादी"], "dada": ["दादा"], "nana": ["नाना"], "nani": ["नानी"], "bhaiya": ["भैया"],
               "didi": ["दीदी"], "chacha": ["चाचा"], "mama": ["मामा"], "bua": ["बुआ"], "mausi": ["मौसी"]}

NOT_LINKED = ("Hi! To use YourHealth here, link your account first: open YourHealth → Connect WhatsApp, "
              "then send me LINK and the 6-digit code.")
BAD_CODE = "That code didn't work or has expired. Make a new one in YourHealth → Connect WhatsApp."
HELP = "I can read PDFs and photos of lab reports and prescriptions, and answer typed questions about them."
TOO_MANY_TRIES = "Too many tries with wrong codes. Please wait an hour, then make a new code in the app."
SEND_AGAIN = "That upload has expired or isn't yours. Please send it again."


def hash_code(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


def handle_message(db: Session, wa: WhatsApp, storage: Storage, queue: DocumentQueue, llm: LLM, msg: dict) -> None:
    phone = "+" + msg["from"].lstrip("+")
    kind = msg.get("type")
    body = (msg.get("text") or {}).get("body", "").strip()

    if kind == "text" and (m := LINK_RE.match(body)):
        return _link(db, wa, phone, m[1])
    link = db.scalar(select(WhatsAppLink).where(WhatsAppLink.phone_e164 == phone))
    if link is None:
        return wa.send_text(phone, NOT_LINKED)

    if kind in ("document", "image"):
        return _ask_whose_report(db, wa, link, msg[kind])
    if kind == "interactive":
        reply = msg["interactive"].get("button_reply") or msg["interactive"].get("list_reply") or {}
        return _on_choice(db, wa, storage, queue, link, reply.get("id", ""))
    if kind == "text" and body.lower() == "switch":
        return _choose(wa, phone, "Who should questions be about?", "ask", _profiles(db, link.user_id, "view"))
    if kind == "text" and body:
        return _answer(db, wa, llm, link, body)
    wa.send_text(phone, HELP)


def _link(db: Session, wa: WhatsApp, phone: str, code: str) -> None:
    now = datetime.now(timezone.utc)
    phone_key = {"phone_sha256": hashlib.sha256(phone.encode()).hexdigest()}  # audit without the number itself
    recent_failures = db.scalar(select(func.count()).select_from(AuditEvent).where(
        AuditEvent.action == "whatsapp.link", AuditEvent.outcome == "denied", AuditEvent.meta == phone_key,
        AuditEvent.at > now - timedelta(hours=1)))
    if recent_failures >= MAX_LINK_FAILURES_PER_HOUR:
        return wa.send_text(phone, TOO_MANY_TRIES)
    row = db.get(WhatsAppLinkCode, hash_code(code))
    if row is None or row.used_at is not None or row.expires_at <= now:
        record(db, "whatsapp.link", "denied", actor_kind="whatsapp", meta=phone_key)
        db.commit()
        return wa.send_text(phone, BAD_CODE)
    row.used_at = now
    existing = db.scalar(select(WhatsAppLink).where(WhatsAppLink.phone_e164 == phone))
    if existing:  # a phone belongs to one account: re-linking moves it
        db.delete(existing)
        db.flush()
    db.add(WhatsAppLink(user_id=row.user_id, phone_e164=phone, linked_at=now))
    db.commit()
    email = db.get(User, row.user_id).email
    wa.send_text(phone, f"Connected to your YourHealth account ({email[0]}•••@{email.split('@')[1]}). Send me a report "
                        "PDF or photo, or ask a question like \"papa ka sugar kaisa hai?\".")


def _profiles(db: Session, user_id: uuid.UUID, need: str) -> list[Profile]:
    rows = db.execute(select(Profile, ProfileMember.role).join(ProfileMember, ProfileMember.profile_id == Profile.id)
                      .where(ProfileMember.user_id == user_id).order_by(Profile.created_at)).all()
    return [p for p, role in rows if need in _ALLOWED[role]]


def _choose(wa: WhatsApp, phone: str, prompt: str, prefix: str, profiles: list[Profile], extra: str = "") -> None:
    if not profiles:
        return wa.send_text(phone, "Add a family profile in the YourHealth app first.")
    options = [(f"{prefix}:{extra}{p.id}", title) for p, title in zip(profiles, _titles(profiles))]
    if len(options) <= MAX_BUTTONS:
        wa.send_buttons(phone, prompt, options)
    else:
        wa.send_list(phone, prompt, "Choose", options)


def _titles(profiles: list[Profile]) -> list[str]:
    """Display names, numbered when two profiles share one: "Papa", "Papa (2)"."""
    seen: dict[str, int] = {}
    out = []
    for p in profiles:
        seen[p.display_name] = seen.get(p.display_name, 0) + 1
        out.append(p.display_name if seen[p.display_name] == 1 else f"{p.display_name} ({seen[p.display_name]})")
    return out


def _ask_whose_report(db: Session, wa: WhatsApp, link: WhatsAppLink, media: dict) -> None:
    pending = WhatsAppPendingUpload(user_id=link.user_id, phone_e164=link.phone_e164, media_id=media["id"],
                                    mime_type=media.get("mime_type"), filename=media.get("filename"),
                                    expires_at=datetime.now(timezone.utc) + timedelta(minutes=PENDING_MINUTES))
    db.add(pending)
    db.commit()
    _choose(wa, link.phone_e164, "Whose report is this?", "up", _profiles(db, link.user_id, "edit"),
            extra=f"{pending.id}:")


def _on_choice(db: Session, wa: WhatsApp, storage: Storage, queue: DocumentQueue, link: WhatsAppLink,
               choice: str) -> None:
    parts = choice.split(":")
    try:
        ids = [uuid.UUID(p) for p in parts[1:]]
    except ValueError:
        return wa.send_text(link.phone_e164, HELP)
    allowed = {p.id: p for p in _profiles(db, link.user_id, "edit" if parts[0] == "up" else "view")}

    if parts[0] == "ask" and len(ids) == 1 and ids[0] in allowed:
        link.last_profile_id = ids[0]
        db.commit()
        return wa.send_text(link.phone_e164, f"Okay, questions are about {allowed[ids[0]].display_name} now. Ask away.")
    if parts[0] != "up" or len(ids) != 2:
        return wa.send_text(link.phone_e164, HELP)

    pending = db.get(WhatsAppPendingUpload, ids[0])
    profile = allowed.get(ids[1])
    if (pending is None or pending.user_id != link.user_id or profile is None
            or pending.expires_at <= datetime.now(timezone.utc)):
        return wa.send_text(link.phone_e164, SEND_AGAIN)
    try:
        data, _mime = wa.download_media(pending.media_id)
    except (httpx.HTTPError, RuntimeError, KeyError):
        return wa.send_text(link.phone_e164, "I couldn't download that file from WhatsApp. Please send it again.")
    try:
        doc, created = store_upload(db, storage, queue, profile.id, link.user_id, data, pending.filename, "whatsapp")
    except UploadRejected as e:
        return wa.send_text(link.phone_e164, f"I couldn't take this file: {e.message}")
    db.delete(pending)
    link.last_profile_id = profile.id  # questions that follow are most likely about this report
    db.commit()
    if created:
        wa.send_text(link.phone_e164, f"Got it. Reading {profile.display_name}'s report…")
    else:
        wa.send_text(link.phone_e164, f"{profile.display_name} already has this report: "
                                      f"{_url(f'/documents/{doc.id}/review')}")


def _answer(db: Session, wa: WhatsApp, llm: LLM, link: WhatsAppLink, question: str) -> None:
    profiles = _profiles(db, link.user_id, "view")
    pid = _named(question, profiles, link.last_profile_id) or (
        link.last_profile_id if link.last_profile_id in {p.id for p in profiles} else None)
    if pid is None and len(profiles) == 1:
        pid = profiles[0].id
    if pid is None:
        return _choose(wa, link.phone_e164, "Who is this question about? Tap a name, then ask again.", "ask", profiles)

    link.last_profile_id = pid
    db.commit()
    lang = "hi" if DEVANAGARI.search(question) or HINGLISH.search(question) else "en"
    out = answer_chat(db, pid, question, lang, llm)
    name = next(p.display_name for p in profiles if p.id == pid)
    lines = [f"Answering for {name}. (Reply 'switch' to change.)", out.summary]
    lines += [f"• {_readable(c.text)}" for c in out.claims[:MAX_CLAIMS_IN_REPLY]]
    if out.doctor_note:
        lines.append(out.doctor_note)
    lines.append(f"Open: {_url(f'/profiles/{pid}/ask')}")
    wa.send_text(link.phone_e164, "\n".join(lines))


def _named(text: str, profiles: list[Profile], last: uuid.UUID | None) -> uuid.UUID | None:
    """The profile the question names; when two share the name, the one used last."""
    lower = text.lower()
    matches = []
    for p in profiles:
        name = p.display_name.lower()
        names = [name, *HINDI_NAMES.get(name, [])]
        if any(re.search(rf"\b{re.escape(n)}\b", lower) if n.isascii() else n in text for n in names):
            matches.append(p.id)
    return last if last in matches else (matches[0] if matches else None)


def _readable(text: str) -> str:
    """Evidence lines ("lab_result | HbA1c 7.2 % ...") as plain text, like the web app shows them."""
    return re.sub(r"^(lab_result|medicine|drug_info|drug_effect|document) \| ", "", text).replace(" | ", " · ")


def _url(path: str) -> str:
    return settings.public_base_url.rstrip("/") + path


def report_done_message(db: Session, doc: Document) -> str:
    """Sent when a report from WhatsApp has been processed (plan 3.3 step 5)."""
    name = db.get(Profile, doc.profile_id).display_name
    if doc.status == "failed":
        return f"Sorry, I couldn't read {name}'s file. A clearer photo or the original PDF usually works."
    if doc.doc_type == "prescription":
        return f"Done. Saved {name}'s prescription. Please confirm the medicines: {_url(f'/profiles/{doc.profile_id}/medicines')}"
    if doc.doc_type != "lab_report":
        return f"Saved to {name}'s reports: {_url(f'/profiles/{doc.profile_id}')}"
    rows = db.execute(select(LabResult, LabTestRecord.canonical_name)
                      .outerjoin(LabTestRecord, LabTestRecord.id == LabResult.lab_test_id)
                      .where(LabResult.document_id == doc.id).order_by(LabResult.page_no, LabResult.created_at)).all()
    flagged = [f"{test or r.raw_name} {r.raw_value} {r.raw_unit or ''}".strip() + f" ({r.flag})"
               for r, test in rows if r.flag in ("low", "high")][:MAX_CLAIMS_IN_REPLY]
    msg = f"Done. {name}'s report: {len(rows)} tests found."
    if flagged:
        msg += f" Outside the report's range: {', '.join(flagged)}."
    if doc.status == "needs_review":
        msg += " A few values need a quick check."
    return msg + f" Open: {_url(f'/documents/{doc.id}/review')}"


def notify_report_done(db: Session, wa: WhatsApp, document_id: uuid.UUID) -> None:
    """After processing: tell the WhatsApp sender how their report went."""
    doc = db.get(Document, document_id)
    if doc is None or doc.source_channel != "whatsapp" or doc.uploaded_by is None:
        return
    link = db.scalar(select(WhatsAppLink).where(WhatsAppLink.user_id == doc.uploaded_by))
    if link:
        wa.send_text(link.phone_e164, report_done_message(db, doc))
