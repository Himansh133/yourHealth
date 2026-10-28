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
