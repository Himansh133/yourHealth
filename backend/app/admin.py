"""Create an administrator locally: python -m app.admin EMAIL."""
import argparse
from getpass import getpass

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.routes.auth import Credentials
from app.core.security import hash_password
from app.db.models import User
from app.db.session import SessionLocal


def create_admin(db: Session, email: str, password: str) -> User:
    credentials = Credentials(email=email, password=password)
    user = User(email=credentials.email, password_hash=hash_password(credentials.password), account_type="admin")
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError("Email already registered; existing accounts are never promoted by this command.") from None
    return user


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("email")
    args = parser.parse_args()
    password = getpass("Admin password (at least 10 characters): ")
    if password != getpass("Confirm password: "):
        parser.error("Passwords do not match")
    with SessionLocal() as db:
        try:
            user = create_admin(db, args.email, password)
        except ValueError as exc:
            parser.error(str(exc))
        print(f"Created admin: {user.email}")


if __name__ == "__main__":
    main()
