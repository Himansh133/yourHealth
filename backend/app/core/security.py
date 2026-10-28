import uuid
from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash

from app.core.config import settings

_hasher = PasswordHash.recommended()  # Argon2
# Verified against when the email is unknown, so login timing doesn't reveal which emails exist.
_DUMMY_HASH = _hasher.hash("dummy-password-for-timing")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    if password_hash is None:
        _hasher.verify(password, _DUMMY_HASH)
        return False
    return _hasher.verify(password, password_hash)


def create_session_token(user_id: uuid.UUID) -> str:
    exp = datetime.now(timezone.utc) + timedelta(days=settings.session_days)
    return jwt.encode({"sub": str(user_id), "exp": exp}, settings.jwt_secret, algorithm="HS256")


def decode_session_token(token: str) -> uuid.UUID | None:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        return uuid.UUID(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError):
        return None
