"""WhatsApp: linking a phone from the web app (plan 3.3, 6.2) and Meta's webhook (plan 7.4)."""
import secrets
from datetime import datetime, timedelta, timezone

import hmac
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy.dialects.postgresql import insert
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.core.config import settings
from app.db.models import User, WhatsAppLink, WhatsAppLinkCode, WhatsAppMessage
from app.db.session import get_db
from app.services.queue import DocumentQueue, get_queue
from app.services.whatsapp.handler import hash_code

router = APIRouter()
log = logging.getLogger(__name__)

LINK_CODE_MINUTES = 10


class LinkCodeOut(BaseModel):
    code: str  # shown once; the user sends "LINK <code>" to the bot
    expires_at: datetime
    bot_number: str


class LinkStatus(BaseModel):
    linked: bool
    phone: str | None  # masked
    linked_at: datetime | None


def _mask(phone: str) -> str:
    """+919812345210 -> +91 ••••••5210"""
    return f"{phone[:3]} {'•' * (len(phone) - 7)}{phone[-4:]}"


@router.post("/me/whatsapp/link-code", response_model=LinkCodeOut)
def create_link_code(user: User = Depends(current_user), db: Session = Depends(get_db)):
    db.execute(delete(WhatsAppLinkCode).where(WhatsAppLinkCode.user_id == user.id,
                                              WhatsAppLinkCode.used_at.is_(None)))
    code = f"{secrets.randbelow(1_000_000):06d}"
    expires = datetime.now(timezone.utc) + timedelta(minutes=LINK_CODE_MINUTES)
    db.add(WhatsAppLinkCode(code_hash=hash_code(code), user_id=user.id, expires_at=expires))
    db.commit()
    return LinkCodeOut(code=code, expires_at=expires, bot_number=settings.wa_display_number)


@router.get("/me/whatsapp", response_model=LinkStatus)
def link_status(user: User = Depends(current_user), db: Session = Depends(get_db)):
    link = db.scalar(select(WhatsAppLink).where(WhatsAppLink.user_id == user.id))
    if link is None:
        return LinkStatus(linked=False, phone=None, linked_at=None)
    return LinkStatus(linked=True, phone=_mask(link.phone_e164), linked_at=link.linked_at)


@router.delete("/me/whatsapp", status_code=204)
def unlink(user: User = Depends(current_user), db: Session = Depends(get_db)):
    db.execute(delete(WhatsAppLink).where(WhatsAppLink.user_id == user.id))
    db.commit()


# --- Meta's webhook (plan 7.4) ----------------------------------------------------------------------------------

@router.get("/whatsapp/webhook", response_class=PlainTextResponse)
def verify_webhook(mode: str = Query(alias="hub.mode"), token: str = Query(alias="hub.verify_token"),
                   challenge: str = Query(alias="hub.challenge")):
    if not settings.wa_verify_token or mode != "subscribe" or not hmac.compare_digest(token, settings.wa_verify_token):
        raise HTTPException(403, "Verification failed")
    return challenge


@router.post("/whatsapp/webhook")
async def receive_webhook(request: Request, db: Session = Depends(get_db),
                          queue: DocumentQueue = Depends(get_queue)):
    raw = await request.body()
    expected = "sha256=" + hmac.new(settings.wa_app_secret.encode(), raw, "sha256").hexdigest()
    if not settings.wa_app_secret or not hmac.compare_digest(request.headers.get("X-Hub-Signature-256", ""), expected):
        raise HTTPException(403, "Bad signature")

    body = await request.json()
    for entry in body.get("entry", []):
        for change in entry.get("changes", []):
            for msg in change.get("value", {}).get("messages", []):  # "statuses" (sent/read) are ignored
                # Idempotent: Meta retries, and a retried message must not be handled twice.
                new = db.execute(insert(WhatsAppMessage).values(
                    wa_message_id=msg["id"], phone_e164="+" + msg["from"].lstrip("+"), direction="in",
                    kind=msg.get("type", "unknown"), status="received",
                ).on_conflict_do_nothing().returning(WhatsAppMessage.wa_message_id)).first()
                db.commit()
                if new:
                    queue.enqueue_whatsapp(msg)
    return {"ok": True}
