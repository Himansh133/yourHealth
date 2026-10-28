"""The one permission check every profile-scoped route goes through (plan 12.1)."""
import uuid
from typing import Literal

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db.models import ProfileMember

_ALLOWED = {
    "owner": {"view", "edit", "share"},
    "caregiver": {"view", "edit", "share"},
    "viewer": {"view"},
}


def require_profile_access(
    db: Session, user_id: uuid.UUID, profile_id: uuid.UUID, need: Literal["view", "edit", "share"]
) -> ProfileMember:
    member = db.get(ProfileMember, (profile_id, user_id))
    if member is None:
        # 404, not 403: don't reveal that the profile exists.
        raise HTTPException(404, "Profile not found")
    if need not in _ALLOWED[member.role]:
        raise HTTPException(403, "Not allowed")
    return member
