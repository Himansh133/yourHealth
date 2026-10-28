"""Load reference data from refdata/seed into the database. Safe to run again after editing the CSVs.

    cd backend && .venv/bin/python -m app.refdata.load
"""
import csv
import json
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import DrugBrand, DrugBrandIngredient, DrugIngredient, DrugLabEffect
from app.db.session import SessionLocal
from app.services.labs.dictionary import get_lab_dictionary
from app.services.labs.store import lab_test_ids
from app.services.medicines.brands import normalize_brand
from app.services.medicines.composition import parse_composition


def load_reference_data(db: Session, seed: Path | None = None) -> None:
    seed = seed or settings.refdata_dir
    test_ids = lab_test_ids(db, get_lab_dictionary())
    labels = {r["ingredient"]: r for r in map(json.loads, open(seed / "drug_labels.jsonl", encoding="utf-8"))}

    for row in _csv(seed / "drug_ingredients.csv"):
        label = labels.get(row["name"], {})
        values = {
            "name": row["name"],
            "atc_code": row["atc_code"] or None,
            "drug_class": row["drug_class"] or None,
            "rxcui": (label.get("rxcui") or [None])[0],
            "used_for": label.get("used_for") or None,
            "label_url": label.get("source_url"),
        }
        db.execute(insert(DrugIngredient).values(values)
                   .on_conflict_do_update(index_elements=["name"], set_={k: v for k, v in values.items() if k != "name"}))
    ingredient_ids = dict(db.execute(select(DrugIngredient.name, DrugIngredient.id)).all())

    for row in _csv(seed / "drug_brands.csv"):
        values = {"brand_name": row["brand_name"], "brand_normalized": normalize_brand(row["brand_name"]),
                  "composition_raw": row["composition_raw"], "source": row["source"]}
        brand_id = db.scalar(
            insert(DrugBrand).values(values)
            .on_conflict_do_update(index_elements=["brand_name"], set_={k: v for k, v in values.items() if k != "brand_name"})
            .returning(DrugBrand.id)
        )
        db.execute(delete(DrugBrandIngredient).where(DrugBrandIngredient.brand_id == brand_id))
        for c in parse_composition(row["composition_raw"]):
            if c.ingredient not in ingredient_ids:
                raise ValueError(f"{row['brand_name']}: ingredient '{c.ingredient}' is not in drug_ingredients.csv")
            db.add(DrugBrandIngredient(brand_id=brand_id, ingredient_id=ingredient_ids[c.ingredient],
                                       strength_value=c.strength, strength_unit=c.unit))

    # Curated table: replaced as a whole so removed rows disappear too. No patient data points at it.
    db.execute(delete(DrugLabEffect))
    for row in _csv(seed / "drug_lab_effects.csv"):
        label = labels[row["ingredient"]]
        db.add(DrugLabEffect(
            ingredient_id=ingredient_ids[row["ingredient"]],
            lab_test_id=test_ids[row["loinc_code"]],
            direction=row["direction"],
            effect_type=row["effect_type"],
            typical_onset=row["typical_onset"] or None,
            onset_days=int(row["onset_days"]),
            note_en=row["note_en"],
            source_name=f"openFDA label: {row['ingredient']}",
            source_section=row["source_section"],
            source_url=label["source_url"],
            reviewed_by=row.get("reviewed_by") or None,
        ))
    db.commit()


def _csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


if __name__ == "__main__":
    with SessionLocal() as session:
        load_reference_data(session)
    print("reference data loaded")
