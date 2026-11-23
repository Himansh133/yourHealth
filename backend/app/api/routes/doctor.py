"""Doctor account registration; clinical access is added only with patient grants (plan 20)."""
import uuid
from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, StringConstraints
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import doctor_user
from app.api.routes.auth import Credentials, UserOut
from app.core.security import hash_password
from app.db.models import Doctor, User
from app.db.session import get_db

router = APIRouter(prefix="/doctor", tags=["doctor"])
VerificationStatus = Literal["unverified", "verified", "rejected", "suspended"]
RequiredText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
OptionalText = Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)]


class DoctorRegistration(Credentials):
    model_config = ConfigDict(extra="forbid")

    full_name: RequiredText
    registration_number: RequiredText
    registration_council: RequiredText
    specialty: OptionalText | None = None
    clinic_name: OptionalText | None = None


class DoctorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    full_name: str
    registration_number: str
    registration_council: str
    specialty: str | None
    clinic_name: str | None
    verification_status: VerificationStatus
    verified_by: uuid.UUID | None
    verified_at: datetime | None


@router.post("/register", status_code=201, response_model=UserOut)
def register(body: DoctorRegistration, db: Session = Depends(get_db)):
    user = User(email=body.email, password_hash=hash_password(body.password), account_type="doctor")
    db.add(user)
    try:
        db.flush()
        db.add(Doctor(user_id=user.id, **body.model_dump(exclude={"email", "password"})))
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Email already registered") from None
    return user


@router.get("/me", response_model=DoctorOut)
def me(user: User = Depends(doctor_user), db: Session = Depends(get_db)):
    doctor = db.get(Doctor, user.id)
    if doctor is None:
        raise HTTPException(404, "Doctor account not found")
    return doctor
