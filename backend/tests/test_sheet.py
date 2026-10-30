from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.db.models import Document, DrugBrand, LabResult, LabTestRecord
from app.refdata.load import load_reference_data
from app.services.sheet import build_sheet

TODAY = date(2026, 10, 29)


@pytest.fixture
def refdata(db_session):
    load_reference_data(db_session)


@pytest.fixture
def papa(make_user_client, refdata):
    a = make_user_client("a@example.com")
    pid = a.post("/api/v1/profiles", json={"display_name": "Papa", "birth_year": 1968, "sex": "male"}).json()["id"]
    return a, pid


def add_doc(db, pid, on, lab="Dr Lal PathLabs", doc_type="lab_report"):
    doc = Document(profile_id=pid, source_channel="web", storage_key=f"docs/{on}{lab}", mime_type="application/pdf",
                   size_bytes=1, sha256=f"{on}{lab}", doc_type=doc_type, report_date=on, status="done", lab_name=lab)
    db.add(doc)
    db.flush()
    return doc


def add(db, doc, loinc, value, flag, low, high):
    test_id = db.scalar(select(LabTestRecord.id).where(LabTestRecord.loinc_code == loinc))
    r = LabResult(profile_id=doc.profile_id, document_id=doc.id, lab_test_id=test_id, raw_name=loinc, raw_value=value,
                  value_num=Decimal(value), value_canonical=Decimal(value), range_low_canonical=Decimal(low),
                  range_high_canonical=Decimal(high), flag=flag, observed_on=doc.report_date, page_no=1,
                  extraction_method="regex")
    db.add(r)
    db.commit()
    return r


def test_header_has_name_age_and_sex_only(db_session, papa):
    _, pid = papa
    sheet = build_sheet(db_session, pid, date(2026, 5, 1), TODAY, True, today=TODAY)
    assert (sheet.profile.display_name, sheet.profile.age, sheet.profile.sex) == ("Papa", 58, "male")
    assert sheet.generated_on == TODAY


def test_flagged_values_are_latest_out_of_range_with_previous(db_session, papa):
    _, pid = papa
    jan, jun = add_doc(db_session, pid, date(2026, 1, 10)), add_doc(db_session, pid, date(2026, 6, 14), "Thyrocare")
    add(db_session, jan, "4548-4", "8.1", "high", "4.0", "5.6")
    latest = add(db_session, jun, "4548-4", "7.2", "high", "4.0", "5.6")
    add(db_session, jun, "2160-0", "1.05", "normal", "0.7", "1.3")

    sheet = build_sheet(db_session, pid, date(2026, 5, 1), TODAY, True, today=TODAY)

    [f] = sheet.flagged
    assert (f.test_name, f.value, f.unit, f.flag, f.observed_on) == ("HbA1c", Decimal("7.2"), "%", "high", date(2026, 6, 14))
    assert (f.range_low, f.range_high) == (Decimal("4.0"), Decimal("5.6"))
    assert (f.previous.value, f.previous.observed_on) == (Decimal("8.1"), date(2026, 1, 10))
    assert f.document_id == latest.document_id


def test_value_back_in_range_is_not_flagged(db_session, papa):
    _, pid = papa
    add(db_session, add_doc(db_session, pid, date(2026, 5, 10)), "4548-4", "8.1", "high", "4.0", "5.6")
    add(db_session, add_doc(db_session, pid, date(2026, 6, 14), "Thyrocare"), "4548-4", "5.4", "normal", "4.0", "5.6")
    assert build_sheet(db_session, pid, date(2026, 5, 1), TODAY, True, today=TODAY).flagged == []


def test_trends_need_two_points_in_the_period(db_session, papa):
    _, pid = papa
    add(db_session, add_doc(db_session, pid, date(2026, 1, 10)), "4548-4", "8.1", "high", "4.0", "5.6")
    add(db_session, add_doc(db_session, pid, date(2026, 6, 14), "Thyrocare"), "4548-4", "7.2", "high", "4.0", "5.6")

    assert build_sheet(db_session, pid, date(2026, 5, 1), TODAY, True, today=TODAY).trends == []
    [t] = build_sheet(db_session, pid, date(2026, 1, 1), TODAY, True, today=TODAY).trends
    assert t.test_name == "HbA1c"
    assert [(p.observed_on, p.value) for p in t.points] == [(date(2026, 1, 10), Decimal("8.1")),
                                                           (date(2026, 6, 14), Decimal("7.2"))]


def test_reports_in_the_period_are_listed(db_session, papa):
    _, pid = papa
    add_doc(db_session, pid, date(2026, 1, 10))
    june = add_doc(db_session, pid, date(2026, 6, 14), "Thyrocare")
    db_session.commit()
    sheet = build_sheet(db_session, pid, date(2026, 5, 1), TODAY, True, today=TODAY)
    assert [(r.document_id, r.title, r.report_date) for r in sheet.reports] == [(june.id, "Thyrocare", date(2026, 6, 14))]


def test_current_medicines_and_medicine_flags(db_session, papa):
    client, pid = papa
    bid = str(db_session.scalar(select(DrugBrand.id).where(DrugBrand.brand_name == "Glycomet 500")))
    client.post(f"/api/v1/profiles/{pid}/medicines",
                json={"brand_id": bid, "frequency_code": "BD", "started_on": "2023-01-01"})
    # B12 fell on long-term metformin: a flagged insight (plan 9.5)
    add(db_session, add_doc(db_session, pid, date(2022, 11, 1)), "2132-9", "450", "normal", "211", "911")
    add(db_session, add_doc(db_session, pid, date(2026, 6, 14), "Thyrocare"), "2132-9", "180", "low", "211", "911")

    sheet = build_sheet(db_session, pid, date(2026, 5, 1), TODAY, True, today=TODAY)

    [m] = sheet.medicines
    assert (m.name, m.generic, m.frequency, m.started_on) == ("Glycomet 500", "metformin", "twice a day", date(2023, 1, 1))
    assert [f.test_name for f in sheet.medicine_flags] == ["Vitamin B12"]
    assert sheet.medicine_flags[0].source_url


def test_medicines_left_out_when_not_wanted(db_session, papa):
    client, pid = papa
    bid = str(db_session.scalar(select(DrugBrand.id).where(DrugBrand.brand_name == "Glycomet 500")))
    client.post(f"/api/v1/profiles/{pid}/medicines", json={"brand_id": bid})
    sheet = build_sheet(db_session, pid, date(2026, 5, 1), TODAY, False, today=TODAY)
    assert (sheet.medicines, sheet.medicine_flags, sheet.include_medicines) == ([], [], False)


def test_sheet_api_previews_for_members_only(make_user_client, papa):
    client, pid = papa
    resp = client.get(f"/api/v1/profiles/{pid}/sheet", params={"from": "2026-05-01", "to": "2026-10-29"})
    assert resp.status_code == 200
    assert resp.json()["profile"]["display_name"] == "Papa"
    assert make_user_client("b@example.com").get(f"/api/v1/profiles/{pid}/sheet").status_code == 404


def test_converted_values_on_the_sheet_are_rounded(db_session, papa):
    _, pid = papa
    jan, jun = add_doc(db_session, pid, date(2026, 5, 10)), add_doc(db_session, pid, date(2026, 6, 14), "Thyrocare")
    add(db_session, jan, "2132-9", "472", "normal", "200", "900")
    b12 = add(db_session, jun, "2132-9", "272", "low", "300", "900")
    b12.value_num, b12.value_canonical = Decimal("200.6"), Decimal("271.8130")  # printed in pmol/L
    db_session.commit()

    sheet = build_sheet(db_session, pid, date(2026, 5, 1), TODAY, True, today=TODAY)

    [f] = sheet.flagged
    assert f.value == Decimal("272")
    assert f.previous.value == Decimal("472")
    [trend] = [t for t in sheet.trends if t.test_name == "Vitamin B12"]
    assert [p.value for p in trend.points] == [Decimal("472"), Decimal("272")]
