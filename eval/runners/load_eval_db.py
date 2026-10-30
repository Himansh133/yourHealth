"""Load the synthetic patients into a separate database, through the real ingestion pipeline (plan 14.5).

Every generated document goes through the worker (text layer or OCR, parsing, classification, indexing with
embeddings); medicines from each story are added as confirmed. Nothing is copied from the truth files.

Usage (from backend/):
  docker exec major-postgres-1 createdb -U yourhealth yourhealth_eval
  DATABASE_URL=postgresql+psycopg://yourhealth:yourhealth@localhost:5432/yourhealth_eval \\
    PYTHONPATH=.. .venv/bin/python -m eval.runners.load_eval_db [--data ../eval/data/v2]
Writes <data>/eval_db.json (login and patient -> profile ids). Use one database per dataset (yourhealth_eval_v2, ...).
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_password
from app.db.models import Document, DrugBrand, DrugBrandIngredient, Profile, ProfileMedicine, ProfileMember, User
from app.db.session import SessionLocal
from app.refdata.load import load_reference_data
from app.services.extraction.ocr import rapid_ocr
from app.services.medicines.store import set_ingredients
from app.services.storage import MemoryStorage
from app.workers.process_document import run

DATA = Path(__file__).resolve().parents[1] / "data" / "v1"
EMAIL, PASSWORD = "eval@example.com", "eval-password-not-secret"
EVAL_DB = re.compile(r"/yourhealth_eval\w*$")  # yourhealth_eval, yourhealth_eval_v2, ...


def main(data: Path = DATA) -> None:
    if not EVAL_DB.search(settings.database_url):
        sys.exit("Refusing to load: DATABASE_URL must point at an eval database (yourhealth_eval...)")
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=True)

    patients = json.loads((data / "patients.json").read_text())
    truths = [json.loads(f.read_text()) for f in sorted((data / "truth").glob("*.json"))]
    storage = MemoryStorage()
    profiles: dict[str, str] = {}
    with SessionLocal() as db:
        load_reference_data(db)
        user = User(email=EMAIL, password_hash=hash_password(PASSWORD))
        db.add(user)
        db.flush()
        for p in patients:
            profile = Profile(display_name=p["display_name"], birth_year=p["birth_year"], sex=p["sex"])
            db.add(profile)
            db.flush()
            db.add(ProfileMember(profile_id=profile.id, user_id=user.id, role="owner"))
            profiles[p["key"]] = str(profile.id)
            for m in p["medicines"]:
                brand = db.scalar(select(DrugBrand).where(DrugBrand.brand_name == m["brand"]))
                med = ProfileMedicine(profile_id=profile.id, brand_id=brand.id, raw_text=m["brand"],
                                      started_on=date.fromisoformat(m["started_on"]), confirmed_by_user=True)
                db.add(med)
                db.flush()
                set_ingredients(db, med, list(db.scalars(
                    select(DrugBrandIngredient.ingredient_id).where(DrugBrandIngredient.brand_id == brand.id))))
        db.commit()

        for i, t in enumerate(truths, 1):
            content = (data / "docs" / t["file"]).read_bytes()
            mime = "application/pdf" if t["file"].endswith(".pdf") else "image/jpeg"
            sha = hashlib.sha256(content).hexdigest()
            doc = Document(profile_id=profiles[t["patient_key"]], uploaded_by=user.id, source_channel="web",
                           storage_key=f"eval/{sha}", original_filename=t["file"], mime_type=mime,
                           size_bytes=len(content), sha256=sha)
            db.add(doc)
            db.commit()
            storage.put(doc.storage_key, content, mime)
            run(db, storage, doc.id, ocr=rapid_ocr)
            if i % 20 == 0:
                print(f"{i}/{len(truths)} documents", flush=True)

    (data / "eval_db.json").write_text(json.dumps({"email": EMAIL, "password": PASSWORD, "profiles": profiles},
                                                  indent=1))
    print(f"loaded {len(patients)} patients, {len(truths)} documents")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=DATA)
    main(ap.parse_args().data)
