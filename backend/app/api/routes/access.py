import base64
import io
import secrets
import uuid
from datetime import timedelta

import qrcode
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.api.deps import doctor_user, patient_user
from app.core.patient_codes import normalize_patient_code
from app.core.permissions import require_profile_access
from app.db.models import AccessGrant, AccessRequest, AuditEvent, ClinicCode, Profile, ProfileMember, User
from app.db.session import get_db
from app.services.doctor_access import (ConsentIn, audit, now, verified_doctor, limit_action, validate_scope,
    create_grant, grant_out, doctor_info, decide_request, clinic_hash)

router = APIRouter()
LOOKUP_MESSAGE = "If this code exists, the patient has been asked to approve."

class LookupIn(BaseModel):
    patient_code: str = Field(max_length=40)
    reason: str = Field(default="", max_length=500)
    hours: int = Field(default=24, ge=1, le=720)

class RedeemIn(BaseModel):
    patient_code: str = Field(max_length=40)
    code: str = Field(pattern=r"^\d{6}$")

@router.post("/doctor/lookup")
def lookup(body: LookupIn, user: User = Depends(doctor_user), db: Session = Depends(get_db)):
    verified_doctor(db, user)
    limit_action(db, user, "doctor.lookup", 10, 3600)
    profile = db.scalar(select(Profile).where(Profile.public_code == normalize_patient_code(body.patient_code)).with_for_update())
    request = None
    if profile:
        count = db.scalar(select(func.count()).select_from(AccessRequest).where(AccessRequest.profile_id == profile.id,
            AccessRequest.created_at > now() - timedelta(days=1)))
        if count < 3:
            request = AccessRequest(doctor_user_id=user.id, profile_id=profile.id, reason_text=body.reason,
                requested_hours=body.hours, expires_at=now() + timedelta(minutes=30))
            db.add(request)
            db.flush()
            audit(db, "access.requested", user, profile.id, request.id)
    db.commit()
    return {"message": LOOKUP_MESSAGE}

@router.get("/doctor/grants")
def doctor_grants(user: User = Depends(doctor_user), db: Session = Depends(get_db)):
    verified_doctor(db, user)
    grants = db.scalars(select(AccessGrant).where(AccessGrant.doctor_user_id == user.id,
        AccessGrant.revoked_at.is_(None), AccessGrant.expires_at > now()).order_by(AccessGrant.expires_at))
    return [grant_out(db, g) for g in grants]

@router.get("/me/access-requests")
def requests(user: User = Depends(patient_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(AccessRequest).join(ProfileMember, ProfileMember.profile_id == AccessRequest.profile_id)
        .where(ProfileMember.user_id == user.id, ProfileMember.role.in_(["owner", "caregiver"]),
               AccessRequest.status == "pending").order_by(AccessRequest.created_at.desc())).all()
    result = []
    for r in rows:
        if r.expires_at <= now():
            r.status = "expired"
            audit(db, "access.expired", user, r.profile_id, r.id)
            continue
        result.append({"id": r.id, "profile_id": r.profile_id, "display_name": db.get(Profile, r.profile_id).display_name,
            "doctor": doctor_info(db, r.doctor_user_id), "reason_text": r.reason_text, "requested_hours": r.requested_hours,
            "status": r.status, "expires_at": r.expires_at})
    db.commit()
    return result

@router.post("/access-requests/{rid}/approve")
def approve(rid: uuid.UUID, body: ConsentIn, user: User = Depends(patient_user), db: Session = Depends(get_db)):
    return grant_out(db, decide_request(db, user, rid, True, body), patient=True)

@router.post("/access-requests/{rid}/deny")
def deny(rid: uuid.UUID, user: User = Depends(patient_user), db: Session = Depends(get_db)):
    decide_request(db, user, rid, False)
    return {"ok": True}

@router.get("/profiles/{pid}/access-grants")
def grants(pid: uuid.UUID, user: User = Depends(patient_user), db: Session = Depends(get_db)):
    require_profile_access(db, user.id, pid, "share")
    return [grant_out(db, g, patient=True) for g in db.scalars(select(AccessGrant).where(AccessGrant.profile_id == pid)
        .order_by(AccessGrant.created_at.desc()))]

@router.post("/access-grants/{gid}/revoke")
def revoke(gid: uuid.UUID, user: User = Depends(patient_user), db: Session = Depends(get_db)):
    grant = db.get(AccessGrant, gid)
    if grant is None:
        raise HTTPException(404, "Grant not found")
    require_profile_access(db, user.id, grant.profile_id, "share")
    if grant.revoked_at is None:
        grant.revoked_at = now()
        audit(db, "access.revoked", user, grant.profile_id, grant.id)
        db.commit()
    return {"ok": True}

@router.post("/profiles/{pid}/clinic-code")
def clinic_code(pid: uuid.UUID, body: ConsentIn, user: User = Depends(patient_user), db: Session = Depends(get_db)):
    require_profile_access(db, user.id, pid, "share")
    profile = db.scalar(select(Profile).where(Profile.id == pid).with_for_update())
    scope = validate_scope(db, pid, body.scope)
    for old in db.scalars(select(ClinicCode).where(ClinicCode.profile_id == pid, ClinicCode.used_at.is_(None))):
        old.used_at = now()
    while True:
        code = f"{secrets.randbelow(1_000_000):06d}"
        hashed = clinic_hash(pid, code)
        if db.get(ClinicCode, hashed) is None:
            break
    expires = now() + timedelta(minutes=10)
    db.add(ClinicCode(code_hash=hashed, profile_id=pid, created_by=user.id, scope=scope,
        grant_hours=body.hours, expires_at=expires))
    db.commit()
    image = qrcode.make(f"{profile.public_code}:{code}")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return {"code": code, "patient_code": profile.public_code, "expires_at": expires,
        "qr_png_base64": base64.b64encode(buffer.getvalue()).decode()}

@router.post("/doctor/clinic-code/redeem")
def redeem(body: RedeemIn, user: User = Depends(doctor_user), db: Session = Depends(get_db)):
    verified_doctor(db, user)
    limit_action(db, user, "doctor.clinic_attempt", 10, 3600)
    profile = db.scalar(select(Profile).where(Profile.public_code == normalize_patient_code(body.patient_code)).with_for_update())
    row = db.scalar(select(ClinicCode).where(ClinicCode.code_hash == clinic_hash(profile.id, body.code)).with_for_update()) if profile else None
    if row is None or row.used_at or row.expires_at <= now():
        db.commit()
        raise HTTPException(404, "Clinic code unavailable")
    row.used_at = now()
    grant = create_grant(db, row.profile_id, user.id, row.grant_hours, row.scope, "clinic_code")
    audit(db, "access.approved", user, row.profile_id, grant.id)
    db.commit()
    return grant_out(db, grant)

@router.get("/profiles/{pid}/access-history")
def history(pid: uuid.UUID, user: User = Depends(patient_user), db: Session = Depends(get_db)):
    require_profile_access(db, user.id, pid, "share")
    from app.db.models import Doctor
    rows = db.execute(select(AuditEvent, Doctor.full_name).outerjoin(Doctor, Doctor.user_id == AuditEvent.actor_user_id)
        .where(AuditEvent.profile_id == pid, (AuditEvent.action.like("doctor.%") | AuditEvent.action.like("access.%")))
        .order_by(AuditEvent.at.desc()).limit(100))
    return [{"id": e.id, "at": e.at, "action": e.action, "doctor_name": name, "outcome": e.outcome} for e, name in rows]
