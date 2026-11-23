import hashlib
import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import SESSION_COOKIE, current_user
from app.core.config import settings
from app.core.security import create_session_token, hash_password, verify_password
from app.db.models import PasswordResetToken, User

logger = logging.getLogger(__name__)
RESET_TOKEN_TTL = timedelta(minutes=30)
from app.db.session import get_db

router = APIRouter()


class Credentials(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)


class LoginBody(BaseModel):
    email: EmailStr
    password: str = Field(max_length=128)


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str = Field(min_length=32, max_length=128)
    password: str = Field(min_length=10, max_length=128)


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    preferred_language: str
    account_type: Literal["patient", "doctor", "admin"]


@router.post("/auth/register", status_code=201, response_model=UserOut)
def register(body: Credentials, db: Session = Depends(get_db)):
    user = User(email=body.email, password_hash=hash_password(body.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Email already registered")
    return user


@router.post("/auth/password-reset/request", status_code=202)
def request_password_reset(body: PasswordResetRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email))
    if user is not None and user.status == "active":
        raw_token = secrets.token_urlsafe(32)
        db.add(PasswordResetToken(
            user_id=user.id,
            token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
            expires_at=datetime.now(timezone.utc) + RESET_TOKEN_TTL,
        ))
        db.commit()
        logger.info("Local password reset requested for %s: reset_token=%s", user.email, raw_token)
    return {"message": "If that email exists, a reset link has been sent."}


@router.post("/auth/password-reset/confirm", status_code=204)
def confirm_password_reset(body: PasswordResetConfirm, db: Session = Depends(get_db)):
    token = db.scalar(select(PasswordResetToken).where(
        PasswordResetToken.token_hash == hashlib.sha256(body.token.encode()).hexdigest(),
        PasswordResetToken.used_at.is_(None),
    ))
    now = datetime.now(timezone.utc)
    if token is None or token.expires_at <= now:
        raise HTTPException(400, "Reset link is invalid or expired")
    user = db.get(User, token.user_id)
    if user is None or user.status != "active":
        raise HTTPException(400, "Reset link is invalid or expired")
    user.password_hash = hash_password(body.password)
    token.used_at = now
    db.commit()


@router.post("/auth/login", response_model=UserOut)
def login(body: LoginBody, response: Response, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email))
    if not verify_password(body.password, user.password_hash if user else None) or user.status != "active":
        raise HTTPException(401, "Wrong email or password")
    response.set_cookie(
        SESSION_COOKIE,
        create_session_token(user.id),
        max_age=settings.session_days * 86400,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
    )
    return user


@router.post("/auth/logout", status_code=204)
def logout(response: Response):
    response.delete_cookie(SESSION_COOKIE, httponly=True, secure=settings.cookie_secure, samesite="lax")


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(current_user)):
    return user
