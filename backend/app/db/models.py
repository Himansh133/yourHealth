"""ORM models. Mirrors plan section 6; tables are added slice by slice."""
import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import CITEXT, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = _uuid_pk()
    email: Mapped[str] = mapped_column(CITEXT, unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    preferred_language: Mapped[str] = mapped_column(Text, nullable=False, default="en")
    status: Mapped[str] = mapped_column(Text, nullable=False, default="active")


class Profile(TimestampMixin, Base):
    __tablename__ = "profiles"
    __table_args__ = (CheckConstraint("sex IN ('male','female','other','unknown')", name="profiles_sex_check"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    birth_year: Mapped[int | None] = mapped_column(Integer)
    sex: Mapped[str | None] = mapped_column(Text)


class ProfileMember(TimestampMixin, Base):
    __tablename__ = "profile_members"
    __table_args__ = (CheckConstraint("role IN ('owner','caregiver','viewer')", name="profile_members_role_check"),)

    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    role: Mapped[str] = mapped_column(Text, nullable=False)
    relation_label: Mapped[str | None] = mapped_column(Text)
