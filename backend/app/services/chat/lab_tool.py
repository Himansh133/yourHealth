"""SQL tool for value and trend questions (plan 10.4).

The LLM never writes SQL or picks the profile: the router names a test and a mode, and we run a fixed query
on the profile the permission check gave us. Each row carries its lab_result, document and page as citation IDs.
"""
import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Document, LabResult, LabTestRecord

FLAG_TEXT = {"low": "LOW", "high": "HIGH", "normal": "within range"}


@dataclass(frozen=True)
class LabFact:
    lab_result_id: uuid.UUID
    document_id: uuid.UUID
    page_no: int | None
    test_name: str
    value: str
    unit: str | None
    range_low: Decimal | None
    range_high: Decimal | None
    flag: str
    observed_on: date
    lab_name: str | None

    def evidence_text(self) -> str:
        value = " ".join(p for p in (self.test_name, self.value, self.unit) if p)
        if self.range_low is not None and self.range_high is not None:
            value += f" (ref {_num(self.range_low)}-{_num(self.range_high)})"
        elif self.range_low is not None:
            value += f" (ref > {_num(self.range_low)})"
        elif self.range_high is not None:
            value += f" (ref < {_num(self.range_high)})"
        else:
            value += " (no range printed)"
        if self.flag in FLAG_TEXT:
            value += f" {FLAG_TEXT[self.flag]}"
        source = " ".join(p for p in (self.lab_name, f"p.{self.page_no}" if self.page_no else None) if p)
        return " | ".join(p for p in ("lab_result", value, self.observed_on.isoformat(), source) if p)


def _num(d: Decimal) -> str:
    return format(d, "f")


def lab_lookup(db: Session, profile_id: uuid.UUID, loinc_code: str, mode: Literal["latest", "trend", "range"],
               date_from: date | None = None, date_to: date | None = None) -> list[LabFact]:
    """Rows oldest first ('latest' gives just the last one)."""
    q = (
        select(LabResult, LabTestRecord, Document.lab_name)
        .join(LabTestRecord, LabTestRecord.id == LabResult.lab_test_id)
        .join(Document, Document.id == LabResult.document_id)
        .where(LabResult.profile_id == profile_id, LabTestRecord.loinc_code == loinc_code)
        .order_by(LabResult.observed_on, LabResult.created_at)
    )
    if date_from:
        q = q.where(LabResult.observed_on >= date_from)
    if date_to:
        q = q.where(LabResult.observed_on <= date_to)
    facts = [_fact(r, t, lab) for r, t, lab in db.execute(q).all()]
    return facts[-1:] if mode == "latest" else facts


def _fact(r: LabResult, t: LabTestRecord, lab_name: str | None) -> LabFact:
    # Canonical unit when we could convert, so values from different labs compare; otherwise as printed.
    if r.value_canonical is not None:
        value, unit = _num(r.value_canonical), t.canonical_unit
    else:
        value, unit = r.raw_value, r.raw_unit
    return LabFact(lab_result_id=r.id, document_id=r.document_id, page_no=r.page_no, test_name=t.canonical_name,
                   value=value, unit=unit, range_low=r.range_low_canonical, range_high=r.range_high_canonical,
                   flag=r.flag, observed_on=r.observed_on, lab_name=lab_name)
