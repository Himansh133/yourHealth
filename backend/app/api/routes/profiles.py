import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.core.permissions import require_profile_access
from app.db.models import Profile, ProfileMember, User
from app.db.session import get_db

router = APIRouter()

Sex = Literal["male", "female", "other", "unknown"]


class ProfileIn(BaseModel):
    display_name: str = Field(min_length=1, max_length=60)
    birth_year: int | None = Field(default=None, ge=1900, le=2100)
    sex: Sex | None = None
    relation_label: str | None = Field(default=None, max_length=40)


class ProfilePatch(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=60)
    birth_year: int | None = Field(default=None, ge=1900, le=2100)
    sex: Sex | None = None
    relation_label: str | None = Field(default=None, max_length=40)


class ProfileOut(BaseModel):
    id: uuid.UUID
    display_name: str
    birth_year: int | None
    sex: str | None
    role: str
    relation_label: str | None


def _out(profile: Profile, member: ProfileMember) -> ProfileOut:
    return ProfileOut(
        id=profile.id,
        display_name=profile.display_name,
        birth_year=profile.birth_year,
        sex=profile.sex,
        role=member.role,
        relation_label=member.relation_label,
    )


@router.get("/profiles", response_model=list[ProfileOut])
def list_profiles(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.execute(
        select(Profile, ProfileMember)
        .join(ProfileMember, ProfileMember.profile_id == Profile.id)
        .where(ProfileMember.user_id == user.id)
        .order_by(Profile.created_at)
    ).all()
    return [_out(p, m) for p, m in rows]


@router.post("/profiles", status_code=201, response_model=ProfileOut)
def create_profile(body: ProfileIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    profile = Profile(display_name=body.display_name, birth_year=body.birth_year, sex=body.sex)
    db.add(profile)
    db.flush()
    member = ProfileMember(profile_id=profile.id, user_id=user.id, role="owner", relation_label=body.relation_label)
    db.add(member)
    db.commit()
    return _out(profile, member)


@router.patch("/profiles/{pid}", response_model=ProfileOut)
def update_profile(
    pid: uuid.UUID, body: ProfilePatch, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    member = require_profile_access(db, user.id, pid, "edit")
    profile = db.get(Profile, pid)
    changes = body.model_dump(exclude_unset=True)
    if "relation_label" in changes:
        member.relation_label = changes.pop("relation_label")
    for field, value in changes.items():
        setattr(profile, field, value)
    db.commit()
    return _out(profile, member)


@router.delete("/profiles/{pid}", status_code=204)
def delete_profile(pid: uuid.UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    member = require_profile_access(db, user.id, pid, "edit")
    if member.role != "owner":
        # Caregivers can edit, but only the owner can delete the whole profile.
        raise HTTPException(403, "Only the owner can delete a profile")
    db.delete(db.get(Profile, pid))
    db.commit()
