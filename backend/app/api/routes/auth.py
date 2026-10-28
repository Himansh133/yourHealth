import uuid

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import SESSION_COOKIE, current_user
from app.core.config import settings
from app.core.security import create_session_token, hash_password, verify_password
from app.db.models import User
from app.db.session import get_db

router = APIRouter()


class Credentials(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)


class LoginBody(BaseModel):
    email: EmailStr
    password: str = Field(max_length=128)


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    preferred_language: str


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
