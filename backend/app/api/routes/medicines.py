import uuid
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator
from rapidfuzz import fuzz
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.api.routes.labs import TestOut, lab_test_out
from app.core.permissions import require_profile_access
from app.db.models import (
    DrugBrand,
    DrugBrandIngredient,
    DrugIngredient,
    DrugLabEffect,
    LabResult,
    LabTestRecord,
    ProfileMedicine,
    User,
)
from app.db.session import get_db
from app.services.medicines import insights as ins
from app.services.medicines.brands import BrandIndex, normalize_brand
from app.services.medicines.composition import parse_composition
from app.services.medicines.store import effects_for, medicine_ingredients, set_ingredients

router = APIRouter()

Frequency = Literal["OD", "BD", "TDS", "QID", "HS", "SOS"]


# --- reference: search and ingredient info ------------------------------------------------------------------

class IngredientOut(BaseModel):
    id: uuid.UUID
    name: str
    drug_class: str | None
    used_for: str | None


class SearchResult(BaseModel):
    kind: Literal["brand", "ingredient"]
    id: uuid.UUID
    name: str
    composition: str | None = None
    ingredients: list[IngredientOut] = []
    drug_class: str | None = None


def _ingredient_out(i: DrugIngredient) -> IngredientOut:
    return IngredientOut(id=i.id, name=i.name, drug_class=i.drug_class, used_for=i.used_for)


def _brand_ingredients(db: Session, brand_ids: list[uuid.UUID]) -> dict[uuid.UUID, list[DrugIngredient]]:
    out: dict[uuid.UUID, list[DrugIngredient]] = {b: [] for b in brand_ids}
    rows = db.execute(
        select(DrugBrandIngredient.brand_id, DrugIngredient)
        .join(DrugIngredient, DrugIngredient.id == DrugBrandIngredient.ingredient_id)
        .where(DrugBrandIngredient.brand_id.in_(brand_ids))
    ).all()
    for brand_id, ing in rows:
        out[brand_id].append(ing)
    return out


@router.get("/drugs/search", response_model=list[SearchResult])
def search_drugs(q: str, _: User = Depends(current_user), db: Session = Depends(get_db)):
    """Brand autocomplete (plan 9.1), plus generic names for people who know the molecule."""
    qn = normalize_brand(q)
    if not qn:
        return []
    brands = db.scalars(select(DrugBrand)).all()
    by_name = {b.brand_name: b for b in brands}
    hits = BrandIndex.from_rows([(b.brand_name, b.composition_raw, b.source) for b in brands]).search(q)
    brand_rows = [by_name[h.brand_name] for h in hits]
    ingredients_by_brand = _brand_ingredients(db, [b.id for b in brand_rows])
    # Order a brand's ingredients as printed in its composition.
    order = {h.brand_name: [c.ingredient for c in h.components] for h in hits}

    ingredients = db.scalars(select(DrugIngredient).order_by(DrugIngredient.name)).all()
    starts = [i for i in ingredients if i.name.startswith(qn)]
    fuzzy = [i for i in ingredients if i not in starts and fuzz.partial_ratio(qn, i.name) >= 85]

    def ing_result(i):
        return SearchResult(kind="ingredient", id=i.id, name=i.name, drug_class=i.drug_class)

    def brand_result(b):
        ings = sorted(ingredients_by_brand[b.id], key=lambda i: order[b.brand_name].index(i.name))
        return SearchResult(kind="brand", id=b.id, name=b.brand_name, composition=b.composition_raw,
                            ingredients=[_ingredient_out(i) for i in ings])

    return [ing_result(i) for i in starts] + [brand_result(b) for b in brand_rows] + [ing_result(i) for i in fuzzy]


class EffectOut(BaseModel):
    test: TestOut
    direction: str
    effect_type: str
    typical_onset: str | None
    note_en: str
    source_name: str
    source_section: str
    source_url: str
    reviewed_by: str | None


class IngredientInfo(BaseModel):
    id: uuid.UUID
    name: str
    drug_class: str | None
    atc_code: str | None
    used_for: str | None
    label_url: str | None
    effects: list[EffectOut]


def _effect_out(e: DrugLabEffect, t: LabTestRecord) -> EffectOut:
    return EffectOut(test=lab_test_out(t), direction=e.direction, effect_type=e.effect_type,
                     typical_onset=e.typical_onset, note_en=e.note_en, source_name=e.source_name,
                     source_section=e.source_section, source_url=e.source_url, reviewed_by=e.reviewed_by)


@router.get("/drugs/ingredients/{iid}", response_model=IngredientInfo)
def ingredient_info(iid: uuid.UUID, _: User = Depends(current_user), db: Session = Depends(get_db)):
    i = db.get(DrugIngredient, iid)
    if i is None:
        raise HTTPException(404, "Ingredient not found")
    effects = [_effect_out(e, t) for e, t in effects_for(db, {i.id})]
    return IngredientInfo(id=i.id, name=i.name, drug_class=i.drug_class, atc_code=i.atc_code, used_for=i.used_for,
                          label_url=i.label_url, effects=sorted(effects, key=lambda e: (e.effect_type != "therapeutic", e.test.name)))


# --- a profile's medicines ------------------------------------------------------------------------------------

class MedicineOut(BaseModel):
    id: uuid.UUID
    name: str
    brand_id: uuid.UUID | None
    composition: str | None
    ingredients: list[IngredientOut]
    raw_text: str
    dose_text: str | None
    frequency_code: str | None
    started_on: date | None
    stopped_on: date | None
    confirmed_by_user: bool
    source_document_id: uuid.UUID | None


def _check_dates(started_on: date | None, stopped_on: date | None) -> None:
    if started_on and started_on > date.today():
        raise ValueError("start date can't be in the future")
    if started_on and stopped_on and stopped_on < started_on:
        raise ValueError("stop date must be on or after the start date")


class MedicineIn(BaseModel):
    brand_id: uuid.UUID | None = None
    ingredient_id: uuid.UUID | None = None
    dose_text: str | None = Field(default=None, max_length=50)
    frequency_code: Frequency | None = None
    started_on: date | None = None
    stopped_on: date | None = None

    @model_validator(mode="after")
    def check(self):
        if (self.brand_id is None) == (self.ingredient_id is None):
            raise ValueError("give exactly one of brand_id or ingredient_id")
        _check_dates(self.started_on, self.stopped_on)
        return self


class MedicinePatch(BaseModel):
    brand_id: uuid.UUID | None = None
    dose_text: str | None = Field(default=None, max_length=50)
    frequency_code: Frequency | None = None
    started_on: date | None = None
    stopped_on: date | None = None
    confirmed_by_user: Literal[True] | None = None  # confirming is one-way; reject by deleting


def medicines_out(db: Session, profile_id: uuid.UUID) -> list[MedicineOut]:
    meds = db.scalars(
        select(ProfileMedicine).where(ProfileMedicine.profile_id == profile_id).order_by(ProfileMedicine.created_at)
    ).all()
    ings: dict[uuid.UUID, list[DrugIngredient]] = {m.id: [] for m in meds}
    for mi in medicine_ingredients(db, profile_id):
        ings[mi.medicine.id].append(mi.ingredient)
    brands = {b.id: b for b in db.scalars(select(DrugBrand).where(DrugBrand.id.in_([m.brand_id for m in meds if m.brand_id])))}
    out = []
    for m in meds:
        brand = brands.get(m.brand_id)
        if brand:  # as printed on the pack: "Metformin + Glimepiride"
            order = [c.ingredient for c in parse_composition(brand.composition_raw)]
            ings[m.id].sort(key=lambda i: order.index(i.name) if i.name in order else len(order))
        names = [i.name for i in ings[m.id]]
        out.append(MedicineOut(
            id=m.id, name=brand.brand_name if brand else (" + ".join(names) or m.raw_text), brand_id=m.brand_id,
            composition=brand.composition_raw if brand else None, ingredients=[_ingredient_out(i) for i in ings[m.id]],
            raw_text=m.raw_text, dose_text=m.dose_text, frequency_code=m.frequency_code, started_on=m.started_on,
            stopped_on=m.stopped_on, confirmed_by_user=m.confirmed_by_user, source_document_id=m.source_document_id,
        ))
    return out


def _brand_or_404(db: Session, brand_id: uuid.UUID) -> tuple[DrugBrand, list[uuid.UUID]]:
    brand = db.get(DrugBrand, brand_id)
    if brand is None:
        raise HTTPException(404, "Brand not found")
    ids = db.scalars(select(DrugBrandIngredient.ingredient_id).where(DrugBrandIngredient.brand_id == brand.id)).all()
    return brand, list(ids)


def _load_medicine(db: Session, user: User, mid: uuid.UUID, need) -> ProfileMedicine:
    med = db.get(ProfileMedicine, mid)
    if med is None:
        raise HTTPException(404, "Medicine not found")
    require_profile_access(db, user.id, med.profile_id, need)
    return med


@router.get("/profiles/{pid}/medicines", response_model=list[MedicineOut])
def list_medicines(pid: uuid.UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_profile_access(db, user.id, pid, "view")
    return medicines_out(db, pid)


@router.post("/profiles/{pid}/medicines", status_code=201, response_model=MedicineOut)
def add_medicine(pid: uuid.UUID, body: MedicineIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_profile_access(db, user.id, pid, "edit")
    if body.brand_id:
        brand, ingredient_ids = _brand_or_404(db, body.brand_id)
        raw_text = brand.brand_name
    else:
        ingredient = db.get(DrugIngredient, body.ingredient_id)
        if ingredient is None:
            raise HTTPException(404, "Ingredient not found")
        ingredient_ids, raw_text = [ingredient.id], ingredient.name
    med = ProfileMedicine(profile_id=pid, brand_id=body.brand_id, raw_text=raw_text, dose_text=body.dose_text,
                          frequency_code=body.frequency_code, started_on=body.started_on, stopped_on=body.stopped_on,
                          confirmed_by_user=True)  # typed in by the user, so already confirmed
    db.add(med)
    db.flush()
    set_ingredients(db, med, ingredient_ids)
    db.commit()
    return next(m for m in medicines_out(db, pid) if m.id == med.id)


@router.patch("/medicines/{mid}", response_model=MedicineOut)
def update_medicine(mid: uuid.UUID, body: MedicinePatch, user: User = Depends(current_user), db: Session = Depends(get_db)):
    med = _load_medicine(db, user, mid, "edit")
    changes = body.model_dump(exclude_unset=True)
    try:
        _check_dates(changes.get("started_on", med.started_on), changes.get("stopped_on", med.stopped_on))
    except ValueError as e:
        raise HTTPException(422, str(e))
    if "brand_id" in changes and changes["brand_id"]:
        brand, ingredient_ids = _brand_or_404(db, changes["brand_id"])
        set_ingredients(db, med, ingredient_ids)
    for field, value in changes.items():
        setattr(med, field, value)
    db.commit()
    return next(m for m in medicines_out(db, med.profile_id) if m.id == med.id)


@router.delete("/medicines/{mid}", status_code=204)
def delete_medicine(mid: uuid.UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    db.delete(_load_medicine(db, user, mid, "edit"))
    db.commit()


# --- insights (plan 9.5) -------------------------------------------------------------------------------------

class ReadingOut(BaseModel):
    lab_result_id: uuid.UUID
    observed_on: date
    value: float


class InsightOut(BaseModel):
    medicine_id: uuid.UUID
    medicine_name: str
    ingredient: str
    loinc_code: str
    test_name: str
    unit: str
    effect_type: str
    direction: str
    status: str
    flagged: bool
    before: ReadingOut | None
    after: ReadingOut | None
    message: str
    note: str
    source_url: str
    source_section: str


@router.get("/profiles/{pid}/medicine-insights", response_model=list[InsightOut])
def medicine_insights(pid: uuid.UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_profile_access(db, user.id, pid, "view")
    mis = medicine_ingredients(db, pid, confirmed_only=True)
    effects = effects_for(db, {mi.ingredient.id for mi in mis})
    names = {mi.ingredient.id: mi.ingredient.name for mi in mis}
    test_ids = {t.id for _, t in effects}
    readings = db.execute(
        select(LabResult, LabTestRecord.loinc_code)
        .join(LabTestRecord, LabTestRecord.id == LabResult.lab_test_id)
        .where(LabResult.profile_id == pid, LabResult.lab_test_id.in_(test_ids), LabResult.value_canonical.is_not(None))
    ).all() if test_ids else []

    result = ins.compute_insights(
        [ins.Medicine(str(mi.medicine.id), mi.name, mi.ingredient.name, mi.medicine.started_on, mi.medicine.stopped_on)
         for mi in mis],
        [ins.Effect(names[e.ingredient_id], t.loinc_code, t.canonical_name, t.canonical_unit, e.direction,
                    e.effect_type, e.onset_days, e.note_en, e.source_url, e.source_section) for e, t in effects],
        [ins.Reading(str(r.id), loinc, r.observed_on, r.value_canonical) for r, loinc in readings],
    )

    def reading(r):
        return ReadingOut(lab_result_id=r.id, observed_on=r.observed_on, value=r.value) if r else None

    return [InsightOut(**{**i.__dict__, "before": reading(i.before), "after": reading(i.after)}) for i in result]
