import pytest
from fastapi import HTTPException

from app.core.permissions import require_profile_access
from app.db.models import Profile, ProfileMember, User


def _setup(db, role):
    user = User(email=f"{role}@example.com", password_hash="x")
    profile = Profile(display_name="Papa")
    db.add_all([user, profile])
    db.flush()
    if role:
        db.add(ProfileMember(profile_id=profile.id, user_id=user.id, role=role))
    db.commit()
    return user, profile


def test_viewer_can_view(db_session):
    user, profile = _setup(db_session, "viewer")
    member = require_profile_access(db_session, user.id, profile.id, "view")
    assert member.role == "viewer"


@pytest.mark.parametrize("need", ["edit", "share"])
def test_viewer_cannot_edit_or_share(db_session, need):
    user, profile = _setup(db_session, "viewer")
    with pytest.raises(HTTPException) as exc:
        require_profile_access(db_session, user.id, profile.id, need)
    assert exc.value.status_code == 403


@pytest.mark.parametrize("need", ["view", "edit", "share"])
def test_caregiver_has_full_access(db_session, need):
    user, profile = _setup(db_session, "caregiver")
    assert require_profile_access(db_session, user.id, profile.id, need).role == "caregiver"


def test_non_member_gets_404_not_403(db_session):
    user, profile = _setup(db_session, None)
    with pytest.raises(HTTPException) as exc:
        require_profile_access(db_session, user.id, profile.id, "view")
    assert exc.value.status_code == 404
