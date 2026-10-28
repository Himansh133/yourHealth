"""ORM models. Mirrors plan section 6; tables are added slice by slice."""
import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import CITEXT, JSONB, UUID
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


class Document(TimestampMixin, Base):
    __tablename__ = "documents"
    __table_args__ = (UniqueConstraint("profile_id", "sha256", name="documents_profile_sha256_key"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False
    )
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    source_channel: Mapped[str] = mapped_column(Text, nullable=False)  # 'web' | 'whatsapp'
    storage_key: Mapped[str] = mapped_column(Text, nullable=False)
    original_filename: Mapped[str | None] = mapped_column(Text)
    mime_type: Mapped[str] = mapped_column(Text, nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(Text, nullable=False)
    doc_type: Mapped[str] = mapped_column(Text, nullable=False, default="unknown")
    lab_name: Mapped[str | None] = mapped_column(Text)
    report_date: Mapped[date | None] = mapped_column(Date)
    # queued|extracting|parsing|indexing|needs_review|done|failed
    status: Mapped[str] = mapped_column(Text, nullable=False, default="queued")
    error_code: Mapped[str | None] = mapped_column(Text)


class DocumentPage(TimestampMixin, Base):
    __tablename__ = "document_pages"
    __table_args__ = (UniqueConstraint("document_id", "page_no", name="document_pages_document_page_key"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    page_no: Mapped[int] = mapped_column(Integer, nullable=False)
    method: Mapped[str] = mapped_column(Text, nullable=False)  # 'text_layer' | OCR engine name
    text: Mapped[str] = mapped_column(Text, nullable=False)
    ocr_confidence: Mapped[float | None] = mapped_column(Float)  # mean word confidence; null for text layer
    words_json: Mapped[list | None] = mapped_column(JSONB)  # [{text, x0, y0, x1, y1[, conf]}]
    processor_version: Mapped[str] = mapped_column(Text, nullable=False)


class LabTestRecord(TimestampMixin, Base):
    """Row form of refdata/seed/lab_tests.csv, so lab_results can reference a test (plan 6.4)."""

    __tablename__ = "lab_tests"

    id: Mapped[uuid.UUID] = _uuid_pk()
    loinc_code: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    canonical_name: Mapped[str] = mapped_column(Text, nullable=False)
    display_name_hi: Mapped[str | None] = mapped_column(Text)
    canonical_unit: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str | None] = mapped_column(Text)


class LabResult(TimestampMixin, Base):
    __tablename__ = "lab_results"
    __table_args__ = (Index("lab_results_profile_test_date_idx", "profile_id", "lab_test_id", "observed_on"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    lab_test_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("lab_tests.id"))
    raw_name: Mapped[str] = mapped_column(Text, nullable=False)
    raw_value: Mapped[str] = mapped_column(Text, nullable=False)
    raw_unit: Mapped[str | None] = mapped_column(Text)
    raw_range: Mapped[str | None] = mapped_column(Text)
    printed_flag: Mapped[str | None] = mapped_column(Text)  # 'H' | 'L' as printed (plan 8.4)
    value_num: Mapped[Decimal | None] = mapped_column(Numeric)
    value_canonical: Mapped[Decimal | None] = mapped_column(Numeric)
    qualifier: Mapped[str | None] = mapped_column(Text)
    range_low: Mapped[Decimal | None] = mapped_column(Numeric)
    range_high: Mapped[Decimal | None] = mapped_column(Numeric)
    range_low_canonical: Mapped[Decimal | None] = mapped_column(Numeric)
    range_high_canonical: Mapped[Decimal | None] = mapped_column(Numeric)
    flag: Mapped[str] = mapped_column(Text, nullable=False)  # low|high|normal|no_range|non_numeric
    observed_on: Mapped[date] = mapped_column(Date, nullable=False)
    page_no: Mapped[int | None] = mapped_column(Integer)
    bbox: Mapped[dict | None] = mapped_column(JSONB)
    extraction_method: Mapped[str] = mapped_column(Text, nullable=False)
    extraction_confidence: Mapped[float | None] = mapped_column(Float)
    verified_by_user: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
