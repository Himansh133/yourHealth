from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.db.models import Document, DrugBrand, DrugIngredient, LabResult, LabTestRecord, ProfileMember, User
from app.refdata.load import load_reference_data

PAPA = {"display_name": "Papa"}


@pytest.fixture
def refdata(db_session):
    load_reference_data(db_session)


def brand_id(db, name):
    return str(db.scalar(select(DrugBrand.id).where(DrugBrand.brand_name == name)))


def ingredient_id(db, name):
    return str(db.scalar(select(DrugIngredient.id).where(DrugIngredient.name == name)))


def add_reading(db, pid, loinc, on, value):
    doc = Document(profile_id=pid, source_channel="web", storage_key=f"docs/{loinc}{on}", mime_type="application/pdf",
                   size_bytes=1, sha256=f"{loinc}{on}", doc_type="lab_report", report_date=on, status="done")
    db.add(doc)
    db.flush()
    test_id = db.scalar(select(LabTestRecord.id).where(LabTestRecord.loinc_code == loinc))
    db.add(LabResult(profile_id=pid, document_id=doc.id, lab_test_id=test_id, raw_name=loinc, raw_value=value,
                     value_num=Decimal(value), value_canonical=Decimal(value), flag="normal", observed_on=on,
                     extraction_method="regex", extraction_confidence=0.85))
    db.commit()


# --- search & reference -----------------------------------------------------------

def test_search_returns_brands_with_ingredients_and_generics(make_user_client, refdata):
    a = make_user_client("a@example.com")
    results = a.get("/api/v1/drugs/search", params={"q": "glycomet gp"}).json()
    gp1 = results[0]
    assert (gp1["kind"], gp1["name"]) == ("brand", "Glycomet GP 1")
    assert gp1["composition"] == "Metformin (500mg) + Glimepiride (1mg)"
    assert [i["name"] for i in gp1["ingredients"]] == ["metformin", "glimepiride"]

    generic = a.get("/api/v1/drugs/search", params={"q": "metformin"}).json()
    assert {"kind": "ingredient", "name": "metformin"}.items() <= generic[0].items()


def test_search_requires_login(client, refdata):
    assert client.get("/api/v1/drugs/search", params={"q": "telma"}).status_code == 401


def test_ingredient_info_lists_cited_lab_effects(make_user_client, db_session, refdata):
    a = make_user_client("a@example.com")
    info = a.get(f"/api/v1/drugs/ingredients/{ingredient_id(db_session, 'metformin')}").json()
    assert info["name"] == "metformin"
    assert info["drug_class"] == "biguanide"
    assert info["label_url"].startswith("https://dailymed.nlm.nih.gov/")
    b12 = next(e for e in info["effects"] if e["test"]["name"] == "Vitamin B12")
    assert (b12["direction"], b12["effect_type"]) == ("decrease", "monitor")
    assert b12["source_section"] == "warnings_and_cautions"
    assert b12["source_url"] == info["label_url"]


# --- profile medicines ------------------------------------------------------------------

def test_add_brand_medicine_resolves_ingredients(make_user_client, db_session, refdata):
    a = make_user_client("a@example.com")
    pid = a.post("/api/v1/profiles", json=PAPA).json()["id"]

    resp = a.post(f"/api/v1/profiles/{pid}/medicines", json={
        "brand_id": brand_id(db_session, "Glycomet GP 1"), "frequency_code": "BD", "started_on": "2026-03-01"})

    assert resp.status_code == 201
    med = resp.json()
    assert med["name"] == "Glycomet GP 1"
    assert [i["name"] for i in med["ingredients"]] == ["metformin", "glimepiride"]
    assert med["confirmed_by_user"] is True
    assert med["started_on"] == "2026-03-01"
    assert a.get(f"/api/v1/profiles/{pid}/medicines").json()[0]["id"] == med["id"]


def test_add_generic_medicine(make_user_client, db_session, refdata):
    a = make_user_client("a@example.com")
    pid = a.post("/api/v1/profiles", json=PAPA).json()["id"]
    med = a.post(f"/api/v1/profiles/{pid}/medicines", json={
        "ingredient_id": ingredient_id(db_session, "levothyroxine"), "dose_text": "50 mcg"}).json()
    assert (med["name"], med["dose_text"]) == ("levothyroxine", "50 mcg")


def test_add_needs_brand_or_ingredient(make_user_client, refdata):
    a = make_user_client("a@example.com")
    pid = a.post("/api/v1/profiles", json=PAPA).json()["id"]
    assert a.post(f"/api/v1/profiles/{pid}/medicines", json={"dose_text": "1"}).status_code == 422


def test_stop_date_before_start_rejected(make_user_client, db_session, refdata):
    a = make_user_client("a@example.com")
    pid = a.post("/api/v1/profiles", json=PAPA).json()["id"]
    resp = a.post(f"/api/v1/profiles/{pid}/medicines", json={
        "brand_id": brand_id(db_session, "Telma 40"), "started_on": "2026-03-01", "stopped_on": "2026-01-01"})
    assert resp.status_code == 422


def test_update_and_delete_medicine(make_user_client, db_session, refdata):
    a = make_user_client("a@example.com")
    pid = a.post("/api/v1/profiles", json=PAPA).json()["id"]
    mid = a.post(f"/api/v1/profiles/{pid}/medicines", json={"brand_id": brand_id(db_session, "Telma 40")}).json()["id"]

    med = a.patch(f"/api/v1/medicines/{mid}", json={"stopped_on": "2026-09-01", "frequency_code": "OD"}).json()
    assert (med["stopped_on"], med["frequency_code"]) == ("2026-09-01", "OD")
    assert a.delete(f"/api/v1/medicines/{mid}").status_code == 204
    assert a.get(f"/api/v1/profiles/{pid}/medicines").json() == []


def test_other_user_cannot_see_or_change_medicines(make_user_client, db_session, refdata):
    a = make_user_client("a@example.com")
    b = make_user_client("b@example.com")
    pid = a.post("/api/v1/profiles", json=PAPA).json()["id"]
    mid = a.post(f"/api/v1/profiles/{pid}/medicines", json={"brand_id": brand_id(db_session, "Telma 40")}).json()["id"]
    assert b.get(f"/api/v1/profiles/{pid}/medicines").status_code == 404
    assert b.post(f"/api/v1/profiles/{pid}/medicines", json={"brand_id": brand_id(db_session, "Telma 40")}).status_code == 404
    assert b.patch(f"/api/v1/medicines/{mid}", json={"dose_text": "x"}).status_code == 404
    assert b.delete(f"/api/v1/medicines/{mid}").status_code == 404
    assert b.get(f"/api/v1/profiles/{pid}/medicine-insights").status_code == 404


def test_viewer_can_list_but_not_add(make_user_client, db_session, refdata):
    a = make_user_client("a@example.com")
    v = make_user_client("v@example.com")
    pid = a.post("/api/v1/profiles", json=PAPA).json()["id"]
    v_user = db_session.scalar(select(User).where(User.email == "v@example.com"))
    db_session.add(ProfileMember(profile_id=pid, user_id=v_user.id, role="viewer"))
    db_session.commit()
    assert v.get(f"/api/v1/profiles/{pid}/medicines").status_code == 200
    assert v.post(f"/api/v1/profiles/{pid}/medicines", json={"brand_id": brand_id(db_session, "Telma 40")}).status_code == 403


# --- insights and trend markers (plan 9.5) ----------------------------------------------

def test_insights_for_confirmed_medicine(make_user_client, db_session, refdata):
    a = make_user_client("a@example.com")
    pid = a.post("/api/v1/profiles", json=PAPA).json()["id"]
    a.post(f"/api/v1/profiles/{pid}/medicines", json={
        "brand_id": brand_id(db_session, "Glycomet 500"), "started_on": "2026-03-01"})
    add_reading(db_session, pid, "4548-4", date(2026, 1, 10), "8.1")
    add_reading(db_session, pid, "4548-4", date(2026, 6, 14), "7.2")

    insights = a.get(f"/api/v1/profiles/{pid}/medicine-insights").json()

    hba1c = next(i for i in insights if i["test_name"] == "HbA1c")
    assert hba1c["status"] == "matches_expected"
    assert hba1c["medicine_name"] == "Glycomet 500"
    assert (hba1c["before"]["value"], hba1c["after"]["value"]) == (8.1, 7.2)
    assert hba1c["before"]["lab_result_id"] and hba1c["source_url"].startswith("https://dailymed")
    b12 = next(i for i in insights if i["test_name"] == "Vitamin B12")
    assert b12["status"] == "not_enough_data"


def test_unconfirmed_medicines_are_left_out_of_insights(make_user_client, db_session, refdata):
    from app.db.models import ProfileMedicine

    a = make_user_client("a@example.com")
    pid = a.post("/api/v1/profiles", json=PAPA).json()["id"]
    db_session.add(ProfileMedicine(profile_id=pid, raw_text="Tab Glycomet 500", confirmed_by_user=False,
                                   brand_id=brand_id(db_session, "Glycomet 500"), started_on=date(2026, 3, 1)))
    db_session.commit()
    assert a.get(f"/api/v1/profiles/{pid}/medicine-insights").json() == []


def test_trends_carry_start_and_stop_markers_for_linked_tests(make_user_client, db_session, refdata):
    a = make_user_client("a@example.com")
    pid = a.post("/api/v1/profiles", json=PAPA).json()["id"]
    a.post(f"/api/v1/profiles/{pid}/medicines", json={
        "brand_id": brand_id(db_session, "Glycomet 500"), "started_on": "2026-03-01", "stopped_on": "2026-09-01"})
    for on, v in [(date(2026, 1, 10), "8.1"), (date(2026, 6, 14), "7.2")]:
        add_reading(db_session, pid, "4548-4", on, v)
        add_reading(db_session, pid, "3016-3", on, "2.0")

    trends = {t["test"]["name"]: t for t in a.get(f"/api/v1/profiles/{pid}/trends").json()}

    assert trends["HbA1c"]["markers"] == [
        {"date": "2026-03-01", "kind": "start", "medicine": "Glycomet 500", "ingredient": "metformin",
         "effect_type": "therapeutic"},
        {"date": "2026-09-01", "kind": "stop", "medicine": "Glycomet 500", "ingredient": "metformin",
         "effect_type": "therapeutic"},
    ]
    assert trends["TSH"]["markers"] == []  # metformin has no TSH link


def test_insight_values_from_converted_readings_are_rounded(make_user_client, db_session, refdata):
    a = make_user_client("a@example.com")
    pid = a.post("/api/v1/profiles", json=PAPA).json()["id"]
    a.post(f"/api/v1/profiles/{pid}/medicines", json={
        "brand_id": brand_id(db_session, "Glycomet 500"), "started_on": "2026-03-01"})
    add_reading(db_session, pid, "4548-4", date(2026, 1, 10), "8.1")
    add_reading(db_session, pid, "4548-4", date(2026, 6, 14), "51")
    r = db_session.scalar(select(LabResult).where(LabResult.raw_value == "51"))
    r.value_canonical = Decimal("6.81752")  # printed as 51 mmol/mol
    db_session.commit()

    insights = a.get(f"/api/v1/profiles/{pid}/medicine-insights").json()

    hba1c = next(i for i in insights if i["test_name"] == "HbA1c")
    assert hba1c["after"]["value"] == 6.82
