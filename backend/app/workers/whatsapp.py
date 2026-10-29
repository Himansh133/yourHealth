"""RQ job: handle one incoming WhatsApp message (plan 7.4). Logs ids only, never message text."""
import logging

from app.db.models import WhatsAppMessage
from app.db.session import SessionLocal
from app.services.chat.llm import get_llm_or_unavailable
from app.services.queue import get_queue
from app.services.storage import get_storage
from app.services.whatsapp.client import get_whatsapp
from app.services.whatsapp.handler import handle_message

log = logging.getLogger(__name__)


def handle_whatsapp_message(message: dict) -> None:
    with SessionLocal() as db:
        status = "processed"
        try:
            handle_message(db, get_whatsapp(), get_storage(), get_queue(), get_llm_or_unavailable(), message)
        except Exception:
            db.rollback()
            log.exception("WhatsApp message %s failed", message.get("id"))
            status = "failed"
        row = db.get(WhatsAppMessage, message["id"])
        if row:
            row.status = status
            db.commit()
