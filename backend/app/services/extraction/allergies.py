"""Conservative report proposals: no report statement confirms patient allergy status."""
import re
from sqlalchemy import select
from app.db.models import Allergy, DrugIngredient


def propose_allergies(db, doc, pages):
    existing = set(db.execute(select(Allergy.substance_text, Allergy.page_no).where(Allergy.source_document_id == doc.id)).all())
    ingredients = {i.name.casefold(): i.id for i in db.scalars(select(DrugIngredient))}
    for page in pages:
        for line in page.text.splitlines():
            text = line.strip()
            absent = bool(re.fullmatch(r'(?:allergies?\s*:\s*)?(?:NKDA|no known (?:drug )?allergies)[.!]?', text, re.I))
            match = re.fullmatch(r'(?:allerg(?:y|ies)\s*:\s*|known allergy to\s+)([^.;\n]{1,150})[.]?',text,re.I)
            substance = 'No known drug allergies' if absent else match.group(1).strip() if match else None
            if not substance or substance.casefold() in ('unknown','none','not known','not recorded'):
                continue
            if (substance,page.page_no) in existing:
                continue
            db.add(Allergy(profile_id=doc.profile_id, substance_text=substance, source='document',
                source_document_id=doc.id,page_no=page.page_no,is_absence=absent, confirmed_by_user=False,
                ingredient_id=ingredients.get(substance.casefold())))
            existing.add((substance,page.page_no))
