"""ORM models. Mirrors plan section 6; tables are added slice by slice."""
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Computed,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import CITEXT, JSONB, TSVECTOR, UUID
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



# --- medicines (plan 6.5) -----------------------------------------------------------------------------------

class DrugIngredient(TimestampMixin, Base):
    """Reference data, loaded from refdata/seed by app.refdata.load. Shared by everyone, not patient data."""

    __tablename__ = "drug_ingredients"

    id: Mapped[uuid.UUID] = _uuid_pk()
    name: Mapped[str] = mapped_column(Text, unique=True, nullable=False)  # Indian generic name, e.g. 'paracetamol'
    rxcui: Mapped[str | None] = mapped_column(Text)
    atc_code: Mapped[str | None] = mapped_column(Text)
    drug_class: Mapped[str | None] = mapped_column(Text)
    used_for: Mapped[str | None] = mapped_column(Text)  # first sentence of the label's indications
    label_url: Mapped[str | None] = mapped_column(Text)  # DailyMed page of the label we used


class DrugBrand(TimestampMixin, Base):
    __tablename__ = "drug_brands"

    id: Mapped[uuid.UUID] = _uuid_pk()
    brand_name: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    brand_normalized: Mapped[str] = mapped_column(Text, nullable=False)
    manufacturer: Mapped[str | None] = mapped_column(Text)
    composition_raw: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(Text, nullable=False)


class DrugBrandIngredient(Base):
    __tablename__ = "drug_brand_ingredients"

    brand_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("drug_brands.id", ondelete="CASCADE"), primary_key=True
    )
    ingredient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("drug_ingredients.id", ondelete="CASCADE"), primary_key=True
    )
    strength_value: Mapped[Decimal | None] = mapped_column(Numeric)
    strength_unit: Mapped[str | None] = mapped_column(Text)


class DrugLabEffect(TimestampMixin, Base):
    """Curated (plan 9.4): every row cites an openFDA label section."""

    __tablename__ = "drug_lab_effects"

    id: Mapped[uuid.UUID] = _uuid_pk()
    ingredient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("drug_ingredients.id", ondelete="CASCADE"), nullable=False
    )
    lab_test_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("lab_tests.id"), nullable=False)
    direction: Mapped[str] = mapped_column(Text, nullable=False)  # decrease | increase | either
    effect_type: Mapped[str] = mapped_column(Text, nullable=False)  # therapeutic | monitor
    typical_onset: Mapped[str | None] = mapped_column(Text)
    onset_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    note_en: Mapped[str] = mapped_column(Text, nullable=False)
    note_hi: Mapped[str | None] = mapped_column(Text)
    source_name: Mapped[str] = mapped_column(Text, nullable=False)
    source_section: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    reviewed_by: Mapped[str | None] = mapped_column(Text)


class ProfileMedicine(TimestampMixin, Base):
    __tablename__ = "profile_medicines"

    id: Mapped[uuid.UUID] = _uuid_pk()
    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False
    )
    brand_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("drug_brands.id"))
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    dose_text: Mapped[str | None] = mapped_column(Text)
    frequency_code: Mapped[str | None] = mapped_column(Text)
    started_on: Mapped[date | None] = mapped_column(Date)
    stopped_on: Mapped[date | None] = mapped_column(Date)
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="SET NULL")
    )
    confirmed_by_user: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class ProfileMedicineIngredient(Base):
    __tablename__ = "profile_medicine_ingredients"

    profile_medicine_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profile_medicines.id", ondelete="CASCADE"), primary_key=True
    )
    ingredient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("drug_ingredients.id"), primary_key=True
    )


# --- RAG (plan 6.6) ------------------------------------------------------------------------------------------

class Chunk(TimestampMixin, Base):
    """Searchable piece of a patient document. Keyword search only for now; the plan's embedding column comes
    with the embedding model."""

    __tablename__ = "chunks"
    __table_args__ = (Index("chunks_tsv_idx", "tsv", postgresql_using="gin"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chunk_type: Mapped[str] = mapped_column(Text, nullable=False)  # page_text | section
    page_start: Mapped[int] = mapped_column(Integer, nullable=False)
    page_end: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    # 'simple': no stemming, works the same for English, Hinglish and test names like "TSH"
    tsv = mapped_column(TSVECTOR, Computed("to_tsvector('simple', text)", persisted=True))
    chunker_version: Mapped[str] = mapped_column(Text, nullable=False)


# --- sharing and audit (plan 6.7) ------------------------------------------------------------------------------

class ShareLink(TimestampMixin, Base):
    """A doctor's view of one profile. Only hashes of the token and PIN are stored."""

    __tablename__ = "share_links"

    id: Mapped[uuid.UUID] = _uuid_pk()
    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    token_hash: Mapped[str] = mapped_column(Text, unique=True, nullable=False)  # sha256 of the token in the QR
    pin_hash: Mapped[str] = mapped_column(Text, nullable=False)  # argon2 of the 4-digit PIN
    scope: Mapped[dict] = mapped_column(JSONB, nullable=False)  # {"from", "to", "include_medicines"}
    snapshot_json: Mapped[dict] = mapped_column(JSONB, nullable=False)  # the sheet, frozen at share time
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failed_pin_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))  # null for a share-link viewer
    actor_kind: Mapped[str] = mapped_column(Text, nullable=False)  # user | share_link | whatsapp | system
    profile_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    action: Mapped[str] = mapped_column(Text, nullable=False)  # share.create, share.open, ...
    resource_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    outcome: Mapped[str] = mapped_column(Text, nullable=False)  # ok | denied | error
    meta: Mapped[dict | None] = mapped_column(JSONB)  # minimal, never medical text
