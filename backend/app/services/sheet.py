"""Doctor visit sheet (plan 13.1). Everything comes from SQL; nothing here is written by the LLM."""
import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Document, LabResult, LabTestRecord, Profile, ProfileMedicine
from app.services.chat.medicine_tool import FREQUENCY_TEXT
from app.services.labs.display import shown
from app.services.medicines.store import medicine_ingredients, profile_insights


class SheetProfile(BaseModel):
    display_name: str
    age: int | None
    sex: str | None


class Reading(BaseModel):
    value: Decimal
    observed_on: date


class FlaggedValue(BaseModel):
    test_name: str
    unit: str
    value: Decimal
    flag: str  # low | high
    observed_on: date
    range_low: Decimal | None
    range_high: Decimal | None
    previous: Reading | None
    lab_result_id: uuid.UUID
    document_id: uuid.UUID


class MedicineFlag(BaseModel):
    medicine_name: str
    test_name: str
    message: str
    source_url: str


class TrendLine(BaseModel):
    test_name: str
    unit: str
    range_low: Decimal | None  # from the latest report
    range_high: Decimal | None
    points: list[Reading]


class SheetMedicine(BaseModel):
    name: str
    generic: str
    dose_text: str | None
    frequency: str | None
    started_on: date | None


class SheetReport(BaseModel):
    document_id: uuid.UUID
    doc_type: str
    title: str | None
    report_date: date


class Sheet(BaseModel):
    profile: SheetProfile
    generated_on: date
    date_from: date
    date_to: date
    include_medicines: bool
    flagged: list[FlaggedValue]
    medicine_flags: list[MedicineFlag]
    trends: list[TrendLine]
    medicines: list[SheetMedicine]
    reports: list[SheetReport]


def build_sheet(db: Session, profile_id: uuid.UUID, date_from: date, date_to: date, include_medicines: bool,
                today: date | None = None) -> Sheet:
    today = today or date.today()
    p = db.get(Profile, profile_id)
    flagged, trends = _values(db, profile_id, date_from, date_to)
    return Sheet(
        profile=SheetProfile(display_name=p.display_name, age=today.year - p.birth_year if p.birth_year else None,
                             sex=p.sex),
        generated_on=today, date_from=date_from, date_to=date_to, include_medicines=include_medicines,
        flagged=flagged, trends=trends,
        medicine_flags=_medicine_flags(db, profile_id) if include_medicines else [],
        medicines=_current_medicines(db, profile_id, today) if include_medicines else [],
        reports=_reports(db, profile_id, date_from, date_to),
    )


def _values(db: Session, pid: uuid.UUID, date_from: date, date_to: date) -> tuple[list[FlaggedValue], list[TrendLine]]:
    rows = db.execute(
        select(LabResult, LabTestRecord)
        .join(LabTestRecord, LabTestRecord.id == LabResult.lab_test_id)
        .where(LabResult.profile_id == pid, LabResult.value_canonical.is_not(None), LabResult.observed_on <= date_to)
        .order_by(LabTestRecord.category, LabTestRecord.canonical_name, LabResult.observed_on, LabResult.created_at)
    ).all()
    by_test: dict[str, tuple[LabTestRecord, list[LabResult]]] = {}
    for r, t in rows:
        by_test.setdefault(t.loinc_code, (t, []))[1].append(r)

    flagged, trends = [], []
    for t, series in by_test.values():
        latest = series[-1]
        if latest.observed_on >= date_from and latest.flag in ("low", "high"):
            prev = series[-2] if len(series) > 1 else None
            flagged.append(FlaggedValue(
                test_name=t.canonical_name, unit=t.canonical_unit, value=shown(latest.value_canonical, latest.value_num),
                flag=latest.flag, observed_on=latest.observed_on,
                range_low=shown(latest.range_low_canonical, latest.range_low),
                range_high=shown(latest.range_high_canonical, latest.range_high), lab_result_id=latest.id,
                document_id=latest.document_id,
                previous=Reading(value=shown(prev.value_canonical, prev.value_num), observed_on=prev.observed_on)
                if prev else None))
        in_period = [r for r in series if r.observed_on >= date_from]
        if len(in_period) >= 2:
            trends.append(TrendLine(
                test_name=t.canonical_name, unit=t.canonical_unit,
                range_low=shown(latest.range_low_canonical, latest.range_low),
                range_high=shown(latest.range_high_canonical, latest.range_high),
                points=[Reading(value=shown(r.value_canonical, r.value_num), observed_on=r.observed_on)
                        for r in in_period]))
    return flagged, trends


def _medicine_flags(db: Session, pid: uuid.UUID) -> list[MedicineFlag]:
    return [MedicineFlag(medicine_name=i.medicine_name, test_name=i.test_name, message=i.message,
                         source_url=i.source_url) for i in profile_insights(db, pid) if i.flagged]


def _current_medicines(db: Session, pid: uuid.UUID, today: date) -> list[SheetMedicine]:
    grouped: dict[uuid.UUID, tuple[str, ProfileMedicine, list[str]]] = {}  # combination tablets: one row
    for mi in medicine_ingredients(db, pid, confirmed_only=True):
        if not (mi.medicine.stopped_on and mi.medicine.stopped_on <= today):
            grouped.setdefault(mi.medicine.id, (mi.name, mi.medicine, []))[2].append(mi.ingredient.name)
    return [SheetMedicine(name=name, generic=" + ".join(generics), dose_text=m.dose_text,
                          frequency=FREQUENCY_TEXT.get(m.frequency_code or ""), started_on=m.started_on)
            for name, m, generics in grouped.values()]


def _reports(db: Session, pid: uuid.UUID, date_from: date, date_to: date) -> list[SheetReport]:
    docs = db.scalars(
        select(Document)
        .where(Document.profile_id == pid, Document.report_date.between(date_from, date_to),
               Document.status.in_(["done", "needs_review"]))
        .order_by(Document.report_date)
    ).all()
    return [SheetReport(document_id=d.id, doc_type=d.doc_type, title=d.lab_name or d.original_filename,
                        report_date=d.report_date) for d in docs]
