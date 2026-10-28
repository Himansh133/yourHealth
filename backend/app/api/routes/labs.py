import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.core.permissions import require_profile_access
from app.db.models import LabResult, LabTestRecord, User
from app.db.session import get_db
from app.services.labs.dictionary import get_lab_dictionary

router = APIRouter()


class TestOut(BaseModel):
    loinc_code: str
    name: str
    name_hi: str | None
    unit: str
    category: str | None


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
    test = TestOut(loinc_code=t.loinc_code, name=t.canonical_name, name_hi=t.display_name_hi,
                   unit=t.canonical_unit, category=t.category) if t else None
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
