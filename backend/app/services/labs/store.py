"""Shared between the worker (first extraction) and the review API (user corrections)."""
import uuid

from sqlalchemy import exists, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.db.models import Document, LabResult, LabTestRecord
from app.services.labs.dictionary import LabDictionary
from app.services.labs.normalize import REVIEW_BELOW, NormalizedRow


def normalized_fields(n: NormalizedRow, test_ids: dict[str, uuid.UUID]) -> dict:
    """LabResult columns that come from a normalised row."""
    return {
        "lab_test_id": test_ids[n.test.loinc_code] if n.test else None,
        "raw_name": n.raw.raw_name,
        "raw_value": n.raw.raw_value,
        "raw_unit": n.raw.raw_unit,
        "raw_range": n.raw.raw_range,
        "printed_flag": n.raw.printed_flag,
        "value_num": n.value_num,
        "value_canonical": n.value_canonical,
        "qualifier": n.qualifier,
        "range_low": n.range_low,
        "range_high": n.range_high,
        "range_low_canonical": n.range_low_canonical,
        "range_high_canonical": n.range_high_canonical,
        "flag": n.flag,
        "extraction_confidence": n.confidence,
    }


def refresh_review_status(db: Session, doc: Document) -> None:
    """needs_review <-> done after a correction. Other states (failed, still processing) are left alone."""
    if doc.status not in ("needs_review", "done"):
        return
    doubtful = db.scalar(
        select(
            exists().where(
                LabResult.document_id == doc.id,
                LabResult.extraction_confidence < REVIEW_BELOW,
                LabResult.verified_by_user.is_(False),
            )
        )
    )
    no_date = doc.doc_type == "lab_report" and doc.report_date is None
    doc.status = "needs_review" if doubtful or no_date else "done"


def lab_test_ids(db: Session, d: LabDictionary) -> dict[str, uuid.UUID]:
    """Make sure every dictionary test has a lab_tests row; return loinc_code -> id."""
    db.execute(
        insert(LabTestRecord)
        .values([
            {"id": uuid.uuid4(), "loinc_code": t.loinc_code, "canonical_name": t.canonical_name,
             "display_name_hi": t.display_name_hi, "canonical_unit": t.canonical_unit, "category": t.category}
            for t in d.tests.values()
        ])
        .on_conflict_do_nothing(index_elements=["loinc_code"])
    )
    return dict(db.execute(select(LabTestRecord.loinc_code, LabTestRecord.id)).all())
