"""DB queries shared by the medicines routes and the trends endpoint."""
import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    DrugBrand,
    DrugIngredient,
    DrugLabEffect,
    LabTestRecord,
    ProfileMedicine,
    ProfileMedicineIngredient,
)


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
