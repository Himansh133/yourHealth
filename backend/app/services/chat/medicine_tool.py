"""Medicine tool for chat (plan 10.1): the person's medicine list, what a medicine is for, and the curated,
label-cited lab effects (plan 9.4). Reference data is shared; the medicine list is filtered by profile."""
import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import DrugBrand, DrugBrandIngredient, DrugIngredient
from app.services.medicines.brands import _split
from app.services.medicines.store import effects_for, medicine_ingredients

FREQUENCY_TEXT = {"OD": "once a day", "BD": "twice a day", "TDS": "three times a day", "QID": "four times a day",
                  "HS": "at bedtime", "SOS": "when needed"}
DIRECTION_TEXT = {"decrease": "lowers it", "increase": "raises it", "either": "can change it"}
EFFECT_TYPE_TEXT = {"therapeutic": "intended effect", "monitor": "worth checking"}
MIN_NAME_LENGTH = 4  # brand bases like "pan" are everyday words


@dataclass(frozen=True)
class MedicineFact:
    kind: str  # medicine | drug_info | drug_effect
    text: str
    medicine_id: uuid.UUID | None = None  # for kind=medicine
    url: str | None = None  # label page, for drug_info and drug_effect


def medicine_vocabulary(db: Session) -> dict[str, set[uuid.UUID]]:
    """Lowercase name -> ingredient ids, for generics and for brands without their strength ("glycomet")."""
    vocab: dict[str, set[uuid.UUID]] = {}
    for ing_id, name in db.execute(select(DrugIngredient.id, DrugIngredient.name)).all():
        vocab.setdefault(name.lower(), set()).add(ing_id)
    rows = db.execute(
        select(DrugBrand.brand_normalized, DrugBrandIngredient.ingredient_id)
        .join(DrugBrandIngredient, DrugBrandIngredient.brand_id == DrugBrand.id)
    ).all()
    for normalized, ing_id in rows:
        base = _split(normalized)[0]
        if len(base) >= MIN_NAME_LENGTH:
            vocab.setdefault(base, set()).add(ing_id)
    return vocab


def medicine_facts(db: Session, profile_id: uuid.UUID, ingredient_ids: set[uuid.UUID],
                   loinc_codes: set[str] | None = None) -> list[MedicineFact]:
    """Facts about these ingredients; lab effects only for loinc_codes when given."""
    facts = []
    for mi in medicine_ingredients(db, profile_id):
        if mi.ingredient.id in ingredient_ids:
            m = mi.medicine
            parts = ["medicine", f"{mi.name} ({mi.ingredient.name})" if mi.name != mi.ingredient.name else mi.name,
                     m.dose_text, FREQUENCY_TEXT.get(m.frequency_code or ""),
                     f"started {m.started_on.isoformat()}" if m.started_on else "start date not known",
                     f"stopped {m.stopped_on.isoformat()}" if m.stopped_on else None,
                     "confirmed by the user" if m.confirmed_by_user else "read from a prescription, not yet confirmed"]
            facts.append(MedicineFact("medicine", " | ".join(p for p in parts if p), medicine_id=m.id))

    ingredients = db.scalars(select(DrugIngredient).where(DrugIngredient.id.in_(ingredient_ids))
                             .order_by(DrugIngredient.name)).all()
    for ing in ingredients:
        if ing.used_for:
            name = f"{ing.name} ({ing.drug_class})" if ing.drug_class else ing.name
            facts.append(MedicineFact("drug_info", f"drug_info | {name} is used for: {ing.used_for} | openFDA label",
                                      url=ing.label_url))

    names = {ing.id: ing.name for ing in ingredients}
    for e, t in sorted(effects_for(db, ingredient_ids), key=lambda et: (names[et[0].ingredient_id], et[1].canonical_name)):
        if loinc_codes is not None and t.loinc_code not in loinc_codes:
            continue
        onset = f", shows in {e.typical_onset}" if e.typical_onset else ""
        text = (f"drug_effect | {names[e.ingredient_id]} and {t.canonical_name}: {DIRECTION_TEXT[e.direction]} "
                f"({EFFECT_TYPE_TEXT[e.effect_type]}){onset}. {e.note_en} | openFDA label, {e.source_section}")
        facts.append(MedicineFact("drug_effect", text, url=e.source_url))
    return facts
