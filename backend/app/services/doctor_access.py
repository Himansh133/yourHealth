"""Patient consent and per-request doctor authorization."""
import hashlib
import uuid
from datetime import datetime, timezone, timedelta

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.core.permissions import require_profile_access
from app.db.models import AccessGrant, AccessRequest, AuditEvent, Doctor, Document, Profile, User


def now():
    return datetime.now(timezone.utc)


class ShareScope(BaseModel):
    model_config = ConfigDict(extra="forbid")
    allergies: bool = True
    medicines: bool = True
    labs: bool = True
    documents: bool = True
    excluded_document_ids: list[uuid.UUID] = Field(default_factory=list, max_length=500)


class ConsentIn(BaseModel):
    hours: int = Field(default=24, ge=1, le=720)
    scope: ShareScope = Field(default_factory=ShareScope)


def audit(db, action, actor, pid=None, resource_id=None, outcome="ok", meta=None):
    db.add(AuditEvent(action=action, actor_user_id=actor.id if actor else None, actor_kind="user",
                      profile_id=pid, resource_id=resource_id, outcome=outcome, meta=meta))


def verified_doctor(db, user):
    doctor = db.get(Doctor, user.id)
    if user.account_type != "doctor" or doctor is None or doctor.verification_status != "verified":
        raise HTTPException(403, "Verified doctor account required")
    return doctor


def require_doctor_grant(db: Session, user: User, pid: uuid.UUID, category=None, document_id=None):
    doctor = db.get(Doctor, user.id)
    grant = db.scalar(select(AccessGrant).where(AccessGrant.doctor_user_id == user.id,
        AccessGrant.profile_id == pid, AccessGrant.revoked_at.is_(None), AccessGrant.expires_at > now())
        .order_by(AccessGrant.created_at.desc(), AccessGrant.id.desc()).limit(1))
    denied = user.account_type != "doctor" or not doctor or doctor.verification_status != "verified" or not grant
    if not denied and category:
        denied = not grant.scope.get(category, False)
    if not denied and document_id:
        denied = str(document_id) in grant.scope.get("excluded_document_ids", [])
    if denied:
        audit(db, "access.denied", user, pid, outcome="denied")
        db.commit()
        raise HTTPException(404, "Shared records not found")
    grant.last_used_at = now()
    db.commit()
    return grant


authorize_doctor = require_doctor_grant


def validate_scope(db, pid, scope):
    ids = scope.excluded_document_ids
    if ids:
        found = set(db.scalars(select(Document.id).where(Document.profile_id == pid, Document.id.in_(ids))))
        if set(ids) != found:
            raise HTTPException(422, "Excluded documents must belong to this profile")
    return scope.model_dump(mode="json")


def limit_action(db, user, action, maximum, seconds):
    # Serialize attempts per account, including fake patient codes.
    db.execute(select(User).where(User.id == user.id).with_for_update()).scalar_one()
    count = db.scalar(select(func.count()).select_from(AuditEvent).where(AuditEvent.actor_user_id == user.id,
        AuditEvent.action == action, AuditEvent.at > now() - timedelta(seconds=seconds)))
    if count >= maximum:
        raise HTTPException(429, "Too many attempts. Try again later.")
    audit(db, action, user)
    db.flush()


def doctor_info(db, uid):
    d = db.get(Doctor, uid)
    return {"user_id": d.user_id, "full_name": d.full_name, "registration_number": d.registration_number,
            "registration_council": d.registration_council}


def grant_out(db, grant, patient=False):
    out = {"id": grant.id, "profile_id": grant.profile_id, "display_name": db.get(Profile, grant.profile_id).display_name,
           "expires_at": grant.expires_at, "created_via": grant.created_via}
    if patient:
        out.update(doctor=doctor_info(db, grant.doctor_user_id), scope=grant.scope, revoked_at=grant.revoked_at,
                   last_used_at=grant.last_used_at)
    return out


def create_grant(db, pid, doctor_id, hours, scope, via, request_id=None):
    # One effective grant per doctor/profile; a new consent replaces earlier scope.
    for old in db.scalars(select(AccessGrant).where(AccessGrant.profile_id == pid,
            AccessGrant.doctor_user_id == doctor_id, AccessGrant.revoked_at.is_(None)).with_for_update()):
        old.revoked_at = now()
    grant = AccessGrant(profile_id=pid, doctor_user_id=doctor_id, request_id=request_id,
        created_via=via, scope=scope, expires_at=now() + timedelta(hours=hours))
    db.add(grant)
    db.flush()
    return grant


def decide_request(db, actor, request_id, approve, consent=None):
    request = db.scalar(select(AccessRequest).where(AccessRequest.id == request_id).with_for_update())
    if request is None:
        raise HTTPException(404, "Request not found")
    require_profile_access(db, actor.id, request.profile_id, "share")
    if request.status != "pending":
        raise HTTPException(409, "Request already decided")
    if request.expires_at <= now():
        request.status = "expired"
        audit(db, "access.expired", actor, request.profile_id, request.id)
        db.commit()
        raise HTTPException(410, "Request expired")
    request.status = "approved" if approve else "denied"
    request.decided_at, request.decided_by = now(), actor.id
    grant = None
    if approve:
        consent = consent or ConsentIn()
        doctor = db.get(Doctor, request.doctor_user_id)
        if doctor.verification_status != "verified":
            raise HTTPException(409, "Doctor is no longer verified")
        scope = validate_scope(db, request.profile_id, consent.scope)
        db.execute(select(Profile).where(Profile.id == request.profile_id).with_for_update()).scalar_one()
        grant = create_grant(db, request.profile_id, request.doctor_user_id, consent.hours, scope, "request_approved", request.id)
    audit(db, "access.approved" if approve else "access.denied", actor, request.profile_id, request.id)
    db.commit()
    return grant


def clinic_hash(pid, code):
    return hashlib.sha256(f"{pid}:{code}".encode()).hexdigest()
