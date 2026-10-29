"""Share a doctor visit sheet by QR link + PIN (plan 13.2)."""
import base64
import hashlib
import io
import secrets
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Literal

import qrcode
from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.api.routes.sheets import DEFAULT_PERIOD
from app.core.config import settings
from app.core.permissions import require_profile_access
from app.core.security import (
    create_share_session_token,
    decode_share_session_token,
    hash_password,
    verify_password,
)
from app.db.models import AuditEvent, Document, ShareLink, User
from app.db.session import get_db
from app.services.audit import record
from app.services.sheet import Sheet, build_sheet
from app.services.storage import Storage, get_storage

router = APIRouter()

EXPIRY = {"1h": timedelta(hours=1), "24h": timedelta(hours=24), "7d": timedelta(days=7)}
MAX_PIN_ATTEMPTS = 5
SHARE_COOKIE = "share_session"


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _state(link: ShareLink) -> str:
    if link.revoked_at:
        return "revoked"
    if link.expires_at <= datetime.now(timezone.utc):
        return "expired"
    if link.failed_pin_attempts >= MAX_PIN_ATTEMPTS:
        return "locked"
    return "active"


# --- owner side ------------------------------------------------------------------------------------------------

class ShareIn(BaseModel):
    expires_in: Literal["1h", "24h", "7d"]
    date_from: date | None = Field(default=None, alias="from")
    date_to: date | None = Field(default=None, alias="to")
    include_medicines: bool = True


class ShareCreated(BaseModel):
    share_id: uuid.UUID
    url: str
    pin: str  # shown once, to the user only
    qr_png_base64: str
    expires_at: datetime


class ShareOut(BaseModel):
    id: uuid.UUID
    created_at: datetime
    expires_at: datetime
    state: str  # active | expired | revoked | locked
    scope: dict
    opens: int
    last_opened_at: datetime | None


@router.post("/profiles/{pid}/shares", response_model=ShareCreated, status_code=201)
def create_share(pid: uuid.UUID, body: ShareIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_profile_access(db, user.id, pid, "share")
    token, pin = secrets.token_urlsafe(32), f"{secrets.randbelow(10_000):04d}"
    date_to = body.date_to or date.today()
    date_from = body.date_from or date_to - DEFAULT_PERIOD
    sheet = build_sheet(db, pid, date_from, date_to, body.include_medicines)
    link = ShareLink(
        profile_id=pid, created_by=user.id, token_hash=_hash_token(token), pin_hash=hash_password(pin),
        scope={"from": date_from.isoformat(), "to": date_to.isoformat(), "include_medicines": body.include_medicines},
        snapshot_json=sheet.model_dump(mode="json"), expires_at=datetime.now(timezone.utc) + EXPIRY[body.expires_in],
    )
    db.add(link)
    db.flush()
    record(db, "share.create", "ok", actor_kind="user", actor_user_id=user.id, profile_id=pid, resource_id=link.id,
           meta={"expires_in": body.expires_in})
    db.commit()

    url = f"{settings.public_base_url.rstrip('/')}/s/{token}"
    png = io.BytesIO()
    qrcode.make(url).save(png)
    return ShareCreated(share_id=link.id, url=url, pin=pin, expires_at=link.expires_at,
                        qr_png_base64=base64.b64encode(png.getvalue()).decode())


@router.get("/profiles/{pid}/shares", response_model=list[ShareOut])
def list_shares(pid: uuid.UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_profile_access(db, user.id, pid, "view")
    opens = dict((rid, (n, last)) for rid, n, last in db.execute(
        select(AuditEvent.resource_id, func.count(), func.max(AuditEvent.at))
        .where(AuditEvent.profile_id == pid, AuditEvent.action == "share.open")
        .group_by(AuditEvent.resource_id)
    ).all())
    links = db.scalars(select(ShareLink).where(ShareLink.profile_id == pid).order_by(ShareLink.created_at.desc()))
    return [ShareOut(id=s.id, created_at=s.created_at, expires_at=s.expires_at, state=_state(s), scope=s.scope,
                     opens=opens.get(s.id, (0, None))[0], last_opened_at=opens.get(s.id, (0, None))[1])
            for s in links]


@router.post("/shares/{sid}/revoke", status_code=204)
def revoke_share(sid: uuid.UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    link = db.get(ShareLink, sid)
    if link is None:
        raise HTTPException(404, "Share not found")
    require_profile_access(db, user.id, link.profile_id, "share")
    if link.revoked_at is None:
        link.revoked_at = datetime.now(timezone.utc)
        record(db, "share.revoke", "ok", actor_kind="user", actor_user_id=user.id, profile_id=link.profile_id,
               resource_id=link.id)
        db.commit()


# --- doctor side (no account) ----------------------------------------------------------------------------------

class UnlockIn(BaseModel):
    pin: str = Field(min_length=4, max_length=4)


def _link_by_token(db: Session, token: str) -> ShareLink:
    link = db.scalar(select(ShareLink).where(ShareLink.token_hash == _hash_token(token)))
    if link is None:
        raise HTTPException(404, "Link not found")
    state = _state(link)
    if state in ("revoked", "expired"):
        raise HTTPException(410, "This link has expired or was turned off")
    if state == "locked":
        raise HTTPException(423, "Too many wrong PINs. Ask for a new link.")
    return link


def _unlocked_link(db: Session, token: str, session: str | None) -> ShareLink:
    link = _link_by_token(db, token)
    if session is None or decode_share_session_token(session) != link.id:
        raise HTTPException(401, "Enter the PIN first")
    return link


@router.post("/s/{token}/unlock")
def unlock(token: str, body: UnlockIn, response: Response, db: Session = Depends(get_db)):
    link = _link_by_token(db, token)
    if not verify_password(body.pin, link.pin_hash):
        link.failed_pin_attempts += 1
        record(db, "share.pin_failed", "denied", actor_kind="share_link", profile_id=link.profile_id,
               resource_id=link.id)
        db.commit()
        raise HTTPException(403, "Wrong PIN")
    record(db, "share.open", "ok", actor_kind="share_link", profile_id=link.profile_id, resource_id=link.id)
    db.commit()
    until = min(link.expires_at, datetime.now(timezone.utc) + timedelta(minutes=settings.share_session_minutes))
    response.set_cookie(SHARE_COOKIE, create_share_session_token(link.id, until),
                        max_age=int((until - datetime.now(timezone.utc)).total_seconds()), path=f"/api/v1/s/{token}",
                        httponly=True, secure=settings.cookie_secure, samesite="lax")
    return {"ok": True}


@router.get("/s/{token}/sheet", response_model=Sheet)
def shared_sheet(token: str, share_session: str | None = Cookie(default=None), db: Session = Depends(get_db)):
    return _unlocked_link(db, token, share_session).snapshot_json


@router.get("/s/{token}/documents/{did}")
def shared_document(token: str, did: uuid.UUID, share_session: str | None = Cookie(default=None),
                    db: Session = Depends(get_db), storage: Storage = Depends(get_storage)):
    link = _unlocked_link(db, token, share_session)
    sheet = link.snapshot_json
    in_scope = {r["document_id"] for r in sheet["reports"]} | {f["document_id"] for f in sheet["flagged"]}
    doc = db.get(Document, did)
    if str(did) not in in_scope or doc is None or doc.profile_id != link.profile_id:
        raise HTTPException(404, "Document not found")
    record(db, "share.document_view", "ok", actor_kind="share_link", profile_id=link.profile_id,
           resource_id=link.id, meta={"document_id": str(did)})
    db.commit()
    return Response(storage.get(doc.storage_key), media_type=doc.mime_type, headers={"Content-Disposition": "inline"})
