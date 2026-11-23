import uuid
from typing import Literal, Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, StringConstraints, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import patient_user
from app.core.permissions import require_profile_access
from app.db.models import Allergy, DrugIngredient, ProfileAllergyStatus, User
from app.db.session import get_db
from app.services.doctor_access import now

router = APIRouter()
Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Severity = Literal['mild', 'moderate', 'severe', 'unknown']

class AllergyIn(BaseModel):
    model_config = ConfigDict(extra='forbid')
    substance_text: Text
    ingredient_id: uuid.UUID | None = None
    drug_class: Text | None = None
    reaction_text: str | None = Field(default=None, max_length=500)
    severity: Severity = 'unknown'

class AllergyPatch(BaseModel):
    model_config = ConfigDict(extra='forbid')
    substance_text: Text | None = None
    ingredient_id: uuid.UUID | None = None
    drug_class: Text | None = None
    reaction_text: str | None = Field(default=None, max_length=500)
    severity: Severity | None = None
    confirmed_by_user: bool | None = None

class StatusIn(BaseModel):
    status: Literal['unknown', 'has_allergies', 'none_known_confirmed']


def entry_out(entry):
    return {k: getattr(entry, k) for k in ('id','substance_text','ingredient_id','drug_class','reaction_text',
        'severity','source','source_document_id','page_no','confirmed_by_user','is_absence')}


def set_status(db, pid, status):
    row = db.get(ProfileAllergyStatus, pid)
    if row is None:
        row = ProfileAllergyStatus(profile_id=pid)
        db.add(row)
    row.status = status
    row.confirmed_at = now() if status != 'unknown' else None


def validate_ingredient(db, iid):
    if iid is not None and db.get(DrugIngredient, iid) is None:
        raise HTTPException(422, 'Ingredient not found')

@router.get('/profiles/{pid}/allergies')
def list_allergies(pid: uuid.UUID, user: User = Depends(patient_user), db: Session = Depends(get_db)):
    require_profile_access(db, user.id, pid, 'view')
    status = db.get(ProfileAllergyStatus, pid)
    entries = db.scalars(select(Allergy).where(Allergy.profile_id == pid).order_by(Allergy.substance_text, Allergy.id)).all()
    return {'status': status.status if status else 'unknown', 'confirmed_at': status.confirmed_at if status else None,
            'entries': [entry_out(a) for a in entries]}

@router.post('/profiles/{pid}/allergies', status_code=201)
def add_allergy(pid: uuid.UUID, body: AllergyIn, user: User = Depends(patient_user), db: Session = Depends(get_db)):
    require_profile_access(db, user.id, pid, 'edit')
    validate_ingredient(db, body.ingredient_id)
    entry = Allergy(profile_id=pid, source='patient', confirmed_by_user=True, **body.model_dump())
    db.add(entry)
    set_status(db, pid, 'has_allergies')
    db.commit()
    return entry_out(entry)

@router.patch('/profiles/{pid}/allergies/{aid}')
def edit_allergy(pid: uuid.UUID, aid: uuid.UUID, body: AllergyPatch, user: User = Depends(patient_user), db: Session = Depends(get_db)):
    require_profile_access(db, user.id, pid, 'edit')
    entry = db.get(Allergy, aid)
    if entry is None or entry.profile_id != pid:
        raise HTTPException(404, 'Allergy not found')
    changes = body.model_dump(exclude_unset=True)
    for required in ('substance_text', 'severity', 'confirmed_by_user'):
        if required in changes and changes[required] is None:
            raise HTTPException(422, f'{required} cannot be null')
    validate_ingredient(db, changes.get('ingredient_id'))
    if entry.is_absence and any(k in changes for k in ('substance_text','ingredient_id','drug_class','severity')):
        raise HTTPException(422, 'Confirm or remove this no-known-allergies report statement')
    if entry.is_absence and changes.get('confirmed_by_user'):
        existing = db.scalar(select(Allergy.id).where(Allergy.profile_id == pid, Allergy.is_absence.is_(False)))
        if existing:
            raise HTTPException(409, 'Resolve recorded allergies before confirming none known')
    for k,v in changes.items():
        setattr(entry,k,v)
    if entry.confirmed_by_user:
        set_status(db,pid,'none_known_confirmed' if entry.is_absence else 'has_allergies')
    db.commit()
    return entry_out(entry)

@router.delete('/profiles/{pid}/allergies/{aid}', status_code=204)
def delete_allergy(pid: uuid.UUID, aid: uuid.UUID, user: User = Depends(patient_user), db: Session = Depends(get_db)):
    require_profile_access(db, user.id, pid, 'edit')
    entry = db.get(Allergy, aid)
    if entry is None or entry.profile_id != pid:
        raise HTTPException(404, 'Allergy not found')
    db.delete(entry)
    db.flush()
    if not db.scalar(select(Allergy.id).where(Allergy.profile_id == pid, Allergy.confirmed_by_user.is_(True), Allergy.is_absence.is_(False))):
        set_status(db,pid,'unknown')
    db.commit()

@router.put('/profiles/{pid}/allergy-status')
def allergy_status(pid: uuid.UUID, body: StatusIn, user: User = Depends(patient_user), db: Session = Depends(get_db)):
    require_profile_access(db,user.id,pid,'edit')
    entries = db.scalars(select(Allergy).where(Allergy.profile_id == pid, Allergy.is_absence.is_(False))).all()
    if body.status == 'none_known_confirmed' and entries:
        raise HTTPException(409,'Resolve recorded allergies before confirming none known')
    if body.status == 'has_allergies' and not entries:
        raise HTTPException(422,'Record an allergy first')
    set_status(db,pid,body.status)
    db.commit()
    return {'status': body.status, 'confirmed_at': db.get(ProfileAllergyStatus,pid).confirmed_at}
