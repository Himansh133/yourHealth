from dataclasses import asdict
from datetime import date

from sqlalchemy import select

from app.db.models import Allergy, Document, DrugBrand, LabResult, LabTestRecord, Profile, ProfileAllergyStatus, ProfileMedicine
from app.services.labs.display import shown
from app.services.medicines.store import medicine_ingredients, profile_insights
from app.services.doctor.scope import clinical_scope

FOOTER = 'Compiled from patient-uploaded records. Values may contain extraction errors. Check originals.'


def allergy_view(db, pid):
    entries = db.scalars(select(Allergy).where(Allergy.profile_id == pid).order_by(Allergy.substance_text, Allergy.id)).all()
    status_row = db.scalar(select(ProfileAllergyStatus).where(ProfileAllergyStatus.profile_id == pid))
    status = status_row.status if status_row else 'unknown'
    if status == 'has_allergies' and not any(not a.is_absence for a in entries):
        status = 'unknown'
    confirmed_at = status_row.confirmed_at if status_row and status != 'unknown' else None
    if status == 'none_known_confirmed':
        message = f'Patient confirmed no known allergies on {confirmed_at.date().isoformat()}.' if confirmed_at else 'Patient confirmed no known allergies.'
    elif status == 'has_allergies':
        message = 'Recorded allergies. Check each source and confirmation status.'
    else:
        message = 'No allergy information recorded. Ask the patient.'
    if entries and status == 'unknown':
        message = 'Allergy status has not been confirmed. Review the entries and ask the patient.'
    return {'status': status, 'confirmed_at': confirmed_at, 'message': message,
            'entries': [{key: getattr(a, key) for key in ('id', 'substance_text', 'reaction_text', 'severity', 'source',
                 'source_document_id', 'page_no', 'confirmed_by_user', 'is_absence', 'ingredient_id', 'drug_class')}
                for a in entries]}


def medicines_view(db, pid):
    ingredients = {}
    for mi in medicine_ingredients(db, pid):
        ingredients.setdefault(mi.medicine.id, []).append({'id': mi.ingredient.id, 'name': mi.ingredient.name})
    rows = db.execute(select(ProfileMedicine, DrugBrand.brand_name).outerjoin(DrugBrand, DrugBrand.id == ProfileMedicine.brand_id)
                      .where(ProfileMedicine.profile_id == pid).order_by(ProfileMedicine.created_at.desc())).all()
    result = []
    for m, brand in rows:
        result.append({'id': m.id, 'name': brand or m.raw_text, 'ingredients': ingredients.get(m.id, []),
                       **{k: getattr(m, k) for k in ('dose_text', 'frequency_code', 'started_on', 'stopped_on',
                                                     'source_document_id', 'confirmed_by_user')}})
    return result


def lab_series(db, pid):
    rows = db.execute(select(LabResult, LabTestRecord).join(LabTestRecord, LabTestRecord.id == LabResult.lab_test_id)
                      .where(LabResult.profile_id == pid, LabResult.value_canonical.is_not(None))
                      .order_by(LabResult.observed_on, LabResult.created_at, LabResult.id)).all()
    result = {}
    for reading, test in rows:
        result.setdefault(test.id, (test, []))[1].append(reading)
    return result


def flagged_labs(db, pid):
    result = []
    for test, rows in lab_series(db, pid).values():
        last = rows[-1]
        if last.flag not in ('low', 'high'):
            continue
        previous = rows[-2] if len(rows) > 1 else None
        result.append({'test_name': test.canonical_name, 'unit': test.canonical_unit,
                       'value': shown(last.value_canonical, last.value_num), 'flag': last.flag,
                       'observed_on': last.observed_on, 'range_low': shown(last.range_low_canonical, last.range_low),
                       'range_high': shown(last.range_high_canonical, last.range_high), 'lab_result_id': last.id,
                       'document_id': last.document_id, 'page_no': last.page_no, 'verified_by_user': last.verified_by_user,
                       'previous': {'value': shown(previous.value_canonical, previous.value_num), 'observed_on': previous.observed_on} if previous else None})
    return result


def build_snapshot(db, grant):
    profile = db.get(Profile, grant.profile_id)
    scope = grant.scope
    with clinical_scope(db, grant):
        medicines = medicines_view(db, profile.id) if scope.get('medicines') else []
        reports = db.scalars(select(Document).where(Document.profile_id == profile.id)
                             .order_by(Document.report_date.desc().nullslast(), Document.created_at.desc()).limit(10)).all() if scope.get('documents') else []
        return {'profile': {'id': profile.id, 'display_name': profile.display_name,
                           'age': date.today().year - profile.birth_year if profile.birth_year else None, 'sex': profile.sex},
                'grant': {'id': grant.id, 'expires_at': grant.expires_at},
                'allergies': allergy_view(db, profile.id) if scope.get('allergies') else None,
                'current_medicines': [m for m in medicines if not m['stopped_on'] or m['stopped_on'] > date.today()] if scope.get('medicines') else None,
                'past_medicines': [m for m in medicines if m['stopped_on'] and m['stopped_on'] <= date.today()] if scope.get('medicines') else None,
                'flagged_labs': flagged_labs(db, profile.id) if scope.get('labs') else None,
                'medicine_flags': [asdict(i) for i in profile_insights(db, profile.id) if i.flagged] if scope.get('labs') and scope.get('medicines') else None,
                'reports': [{k: getattr(d, k) for k in ('id', 'original_filename', 'lab_name', 'report_date', 'doc_type')} for d in reports] if scope.get('documents') else None,
                'footer': FOOTER}
