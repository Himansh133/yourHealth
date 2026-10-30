import uuid
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.core.permissions import require_profile_access
from app.db.models import Document, LabResult, LabTestRecord, User
from app.db.session import get_db
from app.services.labs.dictionary import get_lab_dictionary
from app.services.labs.display import shown
from app.services.labs.normalize import REVIEW_BELOW, normalize_row
from app.services.labs.row_parser import RawRow
from app.services.labs.store import lab_test_ids, normalized_fields, refresh_review_status
from app.services.medicines.store import effects_for, medicine_ingredients

router = APIRouter()


class TestOut(BaseModel):
    loinc_code: str
    name: str
    name_hi: str | None
    unit: str
    category: str | None


def lab_test_out(t: LabTestRecord) -> TestOut:
    return TestOut(loinc_code=t.loinc_code, name=t.canonical_name, name_hi=t.display_name_hi,
                   unit=t.canonical_unit, category=t.category)


class LabResultOut(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    test: TestOut | None
    raw_name: str
    raw_value: str
    raw_unit: str | None
    raw_range: str | None
    printed_flag: str | None
    value_num: float | None
    value_canonical: float | None
    qualifier: str | None
    range_low: float | None
    range_high: float | None
    range_low_canonical: float | None
    range_high_canonical: float | None
    flag: str
    observed_on: date
    page_no: int | None
    bbox: dict | None
    extraction_confidence: float | None
    verified_by_user: bool


def result_out(r: LabResult, t: LabTestRecord | None) -> LabResultOut:
    test = lab_test_out(t) if t else None
    fields = {k: getattr(r, k) for k in LabResultOut.model_fields if k != "test"}
    return LabResultOut(test=test, **fields)


@router.get("/profiles/{pid}/lab-results", response_model=list[LabResultOut])
def list_lab_results(
    pid: uuid.UUID,
    test: str | None = None,
    from_: date | None = Query(default=None, alias="from"),
    to: date | None = None,
    document_id: uuid.UUID | None = None,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    require_profile_access(db, user.id, pid, "view")
    q = (
        select(LabResult, LabTestRecord)
        .outerjoin(LabTestRecord, LabTestRecord.id == LabResult.lab_test_id)
        .where(LabResult.profile_id == pid)
        .order_by(LabResult.observed_on.desc(), LabResult.page_no, LabResult.created_at)
    )
    if test is not None:
        match = get_lab_dictionary().match(test)
        if match is None:
            return []
        q = q.where(LabTestRecord.loinc_code == match.test.loinc_code)
    if from_:
        q = q.where(LabResult.observed_on >= from_)
    if to:
        q = q.where(LabResult.observed_on <= to)
    if document_id:
        q = q.where(LabResult.document_id == document_id)
    return [result_out(r, t) for r, t in db.execute(q).all()]


class LabResultPatch(BaseModel):
    raw_name: str | None = Field(default=None, max_length=200)
    raw_value: str | None = Field(default=None, max_length=50)
    raw_unit: str | None = Field(default=None, max_length=50)
    raw_range: str | None = Field(default=None, max_length=100)

    @field_validator("raw_name", "raw_value")
    @classmethod
    def not_blank(cls, v: str | None) -> str | None:
        if v is not None and not v.strip():
            raise ValueError("must not be blank")
        return v.strip() if v else v


@router.patch("/lab-results/{rid}", response_model=LabResultOut)
def correct_lab_result(
    rid: uuid.UUID, body: LabResultPatch, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    """User checked this row against the original (plan 3.2). An empty body confirms it as correct."""
    row = db.get(LabResult, rid)
    if row is None:
        raise HTTPException(404, "Lab result not found")
    require_profile_access(db, user.id, row.profile_id, "edit")

    changes = body.model_dump(exclude_unset=True)
    raw = RawRow(
        raw_name=changes.get("raw_name", row.raw_name),
        raw_value=changes.get("raw_value", row.raw_value),
        raw_unit=changes.get("raw_unit", row.raw_unit),
        raw_range=changes.get("raw_range", row.raw_range),
        # A corrected value makes the printed flag meaningless.
        printed_flag=None if "raw_value" in changes else row.printed_flag,
        bbox=row.bbox,
    )
    d = get_lab_dictionary()
    for field, value in normalized_fields(normalize_row(raw, d), lab_test_ids(db, d)).items():
        setattr(row, field, value)
    row.verified_by_user = True
    refresh_review_status(db, db.get(Document, row.document_id))
    db.commit()
    return result_out(row, db.get(LabTestRecord, row.lab_test_id) if row.lab_test_id else None)


class TrendPoint(BaseModel):
    lab_result_id: uuid.UUID
    document_id: uuid.UUID
    page_no: int | None
    observed_on: date
    value: float  # canonical unit
    qualifier: str | None
    range_low: float | None  # as printed on that report, canonical unit
    range_high: float | None
    flag: str
    low_confidence: bool  # not yet checked by the user and the parser wasn't sure


class MedicineMarker(BaseModel):
    """Vertical line on a trend chart (plan 9.5): a linked medicine was started or stopped."""

    date: date
    kind: Literal["start", "stop"]
    medicine: str
    ingredient: str
    effect_type: str


class Trend(BaseModel):
    test: TestOut
    points: list[TrendPoint]
    latest: TrendPoint
    markers: list[MedicineMarker]


@router.get("/profiles/{pid}/trends", response_model=list[Trend])
def trends(pid: uuid.UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Plan 3.4: pure SQL, no LLM. Only values we could put in the test's canonical unit are plotted."""
    require_profile_access(db, user.id, pid, "view")
    rows = db.execute(
        select(LabResult, LabTestRecord)
        .join(LabTestRecord, LabTestRecord.id == LabResult.lab_test_id)
        .where(LabResult.profile_id == pid, LabResult.value_canonical.is_not(None))
        .order_by(LabTestRecord.category, LabTestRecord.canonical_name, LabResult.observed_on, LabResult.created_at)
    ).all()

    by_test: dict[str, tuple[LabTestRecord, list[TrendPoint]]] = {}
    for r, t in rows:
        point = TrendPoint(
            lab_result_id=r.id,
            document_id=r.document_id,
            page_no=r.page_no,
            observed_on=r.observed_on,
            value=shown(r.value_canonical, r.value_num),
            qualifier=r.qualifier,
            range_low=shown(r.range_low_canonical, r.range_low),
            range_high=shown(r.range_high_canonical, r.range_high),
            flag=r.flag,
            low_confidence=not r.verified_by_user and (r.extraction_confidence or 0) < REVIEW_BELOW,
        )
        by_test.setdefault(t.loinc_code, (t, []))[1].append(point)

    markers = _medicine_markers(db, pid)
    return [
        Trend(test=lab_test_out(t), points=points, latest=points[-1], markers=markers.get(t.loinc_code, []))
        for t, points in by_test.values()
        if len(points) >= 2
    ]


def _medicine_markers(db: Session, pid: uuid.UUID) -> dict[str, list[MedicineMarker]]:
    """Start/stop markers of confirmed medicines, on the tests their label links them to."""
    mis = medicine_ingredients(db, pid, confirmed_only=True)
    by_ingredient: dict[uuid.UUID, list[tuple[str, str]]] = {}
    for e, t in effects_for(db, {mi.ingredient.id for mi in mis}):
        by_ingredient.setdefault(e.ingredient_id, []).append((t.loinc_code, e.effect_type))
    out: dict[str, list[MedicineMarker]] = {}
    for mi in mis:
        for loinc, effect_type in by_ingredient.get(mi.ingredient.id, []):
            for kind, on in (("start", mi.medicine.started_on), ("stop", mi.medicine.stopped_on)):
                if on:
                    out.setdefault(loinc, []).append(MedicineMarker(
                        date=on, kind=kind, medicine=mi.name, ingredient=mi.ingredient.name, effect_type=effect_type))
    return {k: sorted(v, key=lambda m: m.date) for k, v in out.items()}
