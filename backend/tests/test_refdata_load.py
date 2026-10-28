from sqlalchemy import func, select

from app.db.models import DrugBrand, DrugBrandIngredient, DrugIngredient, DrugLabEffect, LabTestRecord
from app.refdata.load import load_reference_data


def count(db, model):
    return db.scalar(select(func.count()).select_from(model))


def test_load_is_complete_and_idempotent(db_session):
    load_reference_data(db_session)
    first = {m.__name__: count(db_session, m) for m in (DrugIngredient, DrugBrand, DrugBrandIngredient, DrugLabEffect, LabTestRecord)}
    load_reference_data(db_session)
    second = {m.__name__: count(db_session, m) for m in (DrugIngredient, DrugBrand, DrugBrandIngredient, DrugLabEffect, LabTestRecord)}

    assert first == second
    assert first["DrugIngredient"] == 23
    assert first["DrugBrand"] == 41
    assert first["DrugLabEffect"] == 32
    assert first["LabTestRecord"] == 18


def test_every_brand_is_linked_to_its_ingredients(db_session):
    load_reference_data(db_session)
    unlinked = db_session.scalars(
        select(DrugBrand.brand_name).where(~DrugBrand.id.in_(select(DrugBrandIngredient.brand_id)))
    ).all()
    assert unlinked == []
    gp1 = db_session.scalar(select(DrugBrand).where(DrugBrand.brand_name == "Glycomet GP 1"))
    names = db_session.scalars(
        select(DrugIngredient.name).join(DrugBrandIngredient, DrugBrandIngredient.ingredient_id == DrugIngredient.id)
        .where(DrugBrandIngredient.brand_id == gp1.id).order_by(DrugIngredient.name)
    ).all()
    assert names == ["glimepiride", "metformin"]


def test_ingredient_gets_label_facts_with_source(db_session):
    load_reference_data(db_session)
    metformin = db_session.scalar(select(DrugIngredient).where(DrugIngredient.name == "metformin"))
    assert metformin.atc_code == "A10BA02"
    assert metformin.used_for and "metformin" in metformin.used_for.lower()
    assert metformin.label_url.startswith("https://dailymed.nlm.nih.gov/")
    assert metformin.rxcui


def test_effects_cite_their_label(db_session):
    load_reference_data(db_session)
    effects = db_session.scalars(select(DrugLabEffect)).all()
    assert all(e.source_url.startswith("https://dailymed.nlm.nih.gov/") for e in effects)
    assert all(e.source_name.startswith("openFDA label: ") for e in effects)
