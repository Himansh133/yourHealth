from fastapi import Cookie, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.security import decode_session_token
from app.db.models import User
from app.db.session import get_db

SESSION_COOKIE = "session"


def current_user(session: str | None = Cookie(default=None), db: Session = Depends(get_db)) -> User:
    user_id = decode_session_token(session) if session else None
    user = db.get(User, user_id) if user_id else None
    if user is None or user.status != "active":
        raise HTTPException(401, "Not logged in")
    return user


def patient_user(user: User = Depends(current_user)) -> User:
    if user.account_type != "patient":
        raise HTTPException(403, "Patient account required")
    return user


def doctor_user(user: User = Depends(current_user)) -> User:
    if user.account_type != "doctor":
        raise HTTPException(403, "Doctor account required")
    return user


def admin_user(user: User = Depends(current_user)) -> User:
    if user.account_type != "admin":
        raise HTTPException(403, "Admin account required")
    return user
