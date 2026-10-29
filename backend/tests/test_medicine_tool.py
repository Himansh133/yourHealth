import pytest
from sqlalchemy import select

from app.db.models import DrugBrand
from app.refdata.load import load_reference_data
from app.services.chat.medicine_tool import medicine_facts, medicine_vocabulary

PAPA = {"display_name": "Papa"}


@pytest.fixture
def refdata(db_session):
    load_reference_data(db_session)


@pytest.fixture
def papa(make_user_client):
    a = make_user_client("a@example.com")
    return a, a.post("/api/v1/profiles", json=PAPA).json()["id"]


def add_medicine(db, client, pid, brand, **extra):
    bid = str(db.scalar(select(DrugBrand.id).where(DrugBrand.brand_name == brand)))
    resp = client.post(f"/api/v1/profiles/{pid}/medicines", json={"brand_id": bid, **extra})
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_vocabulary_knows_generics_and_brands_without_strength(db_session, refdata, papa):
    _, pid = papa
    vocab = medicine_vocabulary(db_session)
    assert vocab["metformin"] == vocab["glycomet"]
    assert len(vocab["glycomet gp"]) == 2  # metformin + glimepiride
    assert "thyronorm" in vocab


def test_facts_for_a_medicine_the_person_takes(db_session, refdata, papa):
    client, pid = papa
    med = add_medicine(db_session, client, pid, "Glycomet 500", frequency_code="BD", started_on="2026-03-01")
    vocab = medicine_vocabulary(db_session)

    facts = medicine_facts(db_session, pid, vocab["glycomet"])

    taken = [f for f in facts if f.kind == "medicine"]
    assert [f.text for f in taken] == ["medicine | Glycomet 500 (metformin) | twice a day | started 2026-03-01 | "
                                       "confirmed by the user"]
    assert str(taken[0].medicine_id) == med["id"]
    info = next(f for f in facts if f.kind == "drug_info")
    assert info.text.startswith("drug_info | metformin (biguanide) is used for: Metformin hydrochloride tablets")
    assert info.url.startswith("https://dailymed.nlm.nih.gov/")
    effects = [f.text for f in facts if f.kind == "drug_effect"]
    assert any(t.startswith("drug_effect | metformin and HbA1c: lowers it (intended effect), shows in about 3 months.")
               for t in effects)


def test_facts_for_a_medicine_the_person_does_not_take(db_session, refdata, papa):
    _, pid = papa
    facts = medicine_facts(db_session, pid, medicine_vocabulary(db_session)["thyronorm"])
    assert [f.kind for f in facts if f.kind == "medicine"] == []
    assert any(f.kind == "drug_info" and "levothyroxine" in f.text for f in facts)


def test_effects_can_be_limited_to_the_asked_tests(db_session, refdata, papa):
    _, pid = papa
    facts = medicine_facts(db_session, pid, medicine_vocabulary(db_session)["metformin"], loinc_codes={"2132-9"})
    effects = [f.text for f in facts if f.kind == "drug_effect"]
    assert len(effects) == 1
    assert "Vitamin B12" in effects[0]


def test_another_profiles_medicines_are_not_used(db_session, refdata, papa, make_user_client):
    other = make_user_client("b@example.com")
    other_pid = other.post("/api/v1/profiles", json=PAPA).json()["id"]
    add_medicine(db_session, other, other_pid, "Glycomet 500")
    _, pid = papa
    facts = medicine_facts(db_session, pid, medicine_vocabulary(db_session)["glycomet"])
    assert [f for f in facts if f.kind == "medicine"] == []
