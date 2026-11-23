"""Manual medical-registration review. Public signup cannot create admin accounts."""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import admin_user
from app.api.routes.doctor import DoctorOut, VerificationStatus
from app.db.models import AuditEvent, Doctor, User
from app.db.session import get_db

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/doctors", response_model=list[DoctorOut])
def list_doctors(status: VerificationStatus = "unverified", _: User = Depends(admin_user),
                 db: Session = Depends(get_db)):
    return db.scalars(select(Doctor).where(Doctor.verification_status == status)
                      .order_by(Doctor.full_name, Doctor.user_id)).all()


def _review(db: Session, actor: User, uid: uuid.UUID, status: str) -> Doctor:
    doctor = db.get(Doctor, uid)
    if doctor is None:
        raise HTTPException(404, "Doctor account not found")
    doctor.verification_status = status
    doctor.verified_by = actor.id if status == "verified" else None
    doctor.verified_at = datetime.now(timezone.utc) if status == "verified" else None
    db.add(AuditEvent(actor_user_id=actor.id, actor_kind="user", resource_id=uid,
                      action=f"doctor.{status}", outcome="ok"))
    db.commit()
    return doctor


@router.post("/doctors/{uid}/verify", response_model=DoctorOut)
def verify(uid: uuid.UUID, actor: User = Depends(admin_user), db: Session = Depends(get_db)):
    return _review(db, actor, uid, "verified")


@router.post("/doctors/{uid}/reject", response_model=DoctorOut)
def reject(uid: uuid.UUID, actor: User = Depends(admin_user), db: Session = Depends(get_db)):
    return _review(db, actor, uid, "rejected")
