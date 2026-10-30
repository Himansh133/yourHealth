"""DB queries shared by the medicines routes, the trends endpoint, chat and the doctor sheet."""
import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    DrugBrand,
    DrugIngredient,
    DrugLabEffect,
    LabResult,
    LabTestRecord,
    ProfileMedicine,
    ProfileMedicineIngredient,
)
from app.services.labs.display import shown
from app.services.medicines import insights as ins


@dataclass(frozen=True)
class MedicineIngredient:
    medicine: ProfileMedicine
    name: str  # what the user calls it: brand name, or the generic name
    ingredient: DrugIngredient


def medicine_ingredients(db: Session, profile_id: uuid.UUID, confirmed_only: bool = False) -> list[MedicineIngredient]:
    q = (
        select(ProfileMedicine, DrugBrand.brand_name, DrugIngredient)
        .outerjoin(DrugBrand, DrugBrand.id == ProfileMedicine.brand_id)
        .join(ProfileMedicineIngredient, ProfileMedicineIngredient.profile_medicine_id == ProfileMedicine.id)
        .join(DrugIngredient, DrugIngredient.id == ProfileMedicineIngredient.ingredient_id)
        .where(ProfileMedicine.profile_id == profile_id)
        .order_by(ProfileMedicine.created_at, DrugIngredient.name)
    )
    if confirmed_only:
        q = q.where(ProfileMedicine.confirmed_by_user.is_(True))
    return [MedicineIngredient(m, brand or ing.name, ing) for m, brand, ing in db.execute(q).all()]


def effects_for(db: Session, ingredient_ids: set[uuid.UUID]) -> list[tuple[DrugLabEffect, LabTestRecord]]:
    if not ingredient_ids:
        return []
    return db.execute(
        select(DrugLabEffect, LabTestRecord)
        .join(LabTestRecord, LabTestRecord.id == DrugLabEffect.lab_test_id)
        .where(DrugLabEffect.ingredient_id.in_(ingredient_ids))
    ).all()


def set_ingredients(db: Session, medicine: ProfileMedicine, ingredient_ids: list[uuid.UUID]) -> None:
    db.query(ProfileMedicineIngredient).filter_by(profile_medicine_id=medicine.id).delete()
    db.add_all(ProfileMedicineIngredient(profile_medicine_id=medicine.id, ingredient_id=i) for i in ingredient_ids)


def profile_insights(db: Session, profile_id: uuid.UUID) -> list[ins.Insight]:
    """Plan 9.5 for every confirmed medicine of this profile, from its own readings."""
    mis = medicine_ingredients(db, profile_id, confirmed_only=True)
    effects = effects_for(db, {mi.ingredient.id for mi in mis})
    names = {mi.ingredient.id: mi.ingredient.name for mi in mis}
    test_ids = {t.id for _, t in effects}
    readings = db.execute(
        select(LabResult, LabTestRecord.loinc_code)
        .join(LabTestRecord, LabTestRecord.id == LabResult.lab_test_id)
        .where(LabResult.profile_id == profile_id, LabResult.lab_test_id.in_(test_ids),
               LabResult.value_canonical.is_not(None))
    ).all() if test_ids else []

    return ins.compute_insights(
        [ins.Medicine(str(mi.medicine.id), mi.name, mi.ingredient.name, mi.medicine.started_on, mi.medicine.stopped_on)
         for mi in mis],
        [ins.Effect(names[e.ingredient_id], t.loinc_code, t.canonical_name, t.canonical_unit, e.direction,
                    e.effect_type, e.onset_days, e.note_en, e.source_url, e.source_section) for e, t in effects],
        [ins.Reading(str(r.id), loinc, r.observed_on, shown(r.value_canonical, r.value_num)) for r, loinc in readings],
    )
