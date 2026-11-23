from datetime import date

from sqlalchemy import select

from app.db.models import Allergy, Document, ProfileMedicine, User
from app.services.storage import MemoryStorage
from eval.runners import import_mimic_demo as importer
from eval.tests.test_import_mimic_demo import write_table


def test_local_import_creates_separate_account_and_keeps_historical_medicines_unconfirmed(tmp_path, db_session, monkeypatch):
    root = tmp_path / 'source'
    write_table(root, 'patients', [{'subject_id': '1', 'gender': 'F'}])
    write_table(root, 'd_labitems', [{'itemid': '10', 'label': 'Creatinine', 'fluid': 'Blood'}])
    write_table(root, 'labevents', [{'subject_id': '1', 'charttime': '2180-01-01 10:00:00', 'value': '1.25', 'valuenum': '1.25', 'valueuom': 'mg/dL', 'ref_range_lower': '0.7', 'ref_range_upper': '1.3', 'itemid': '10', 'labevent_id': '42'}])
    write_table(root, 'prescriptions', [{'subject_id': '1', 'drug': 'Metformin', 'starttime': '2179-12-01 00:00:00', 'stoptime': '2180-01-02 00:00:00', 'dose_val_rx': '500', 'dose_unit_rx': 'mg', 'route': 'PO'}])
    write_table(root, 'admissions', [{'subject_id': '1', 'hadm_id': 'a', 'admittime': '2179-12-01 00:00:00', 'dischtime': '2180-01-02 00:00:00'}])
    monkeypatch.setattr(importer, 'ROOT', tmp_path)
    monkeypatch.setattr('app.db.session.SessionLocal', lambda: db_session)
    monkeypatch.setattr('app.services.storage.get_storage', lambda: MemoryStorage())
    manifest = importer.prepare(root, '1', date(2026, 11, 17))
    state = importer.load_local(root, manifest)
    assert state['status'] == 'complete'
    import uuid
    summary = db_session.get(Document, uuid.UUID(state['documents']['source-history-summary.pdf']))
    assert summary.doc_type == 'other'
    assert len(state['documents']) == 3
    user = db_session.scalar(select(User).where(User.email == state['email']))
    assert user.account_type == 'patient'
    medicines = db_session.scalars(select(ProfileMedicine)).all()
    assert len(medicines) == 1 and medicines[0].raw_text == 'Metformin'
    assert medicines[0].confirmed_by_user is False
    assert medicines[0].stopped_on < date.today()
    assert db_session.scalars(select(Allergy)).all() == []
    credentials = tmp_path / 'passwords.md'
    assert state['email'] in credentials.read_text()
    assert credentials.stat().st_mode & 0o777 == 0o600
    assert 'password' not in (root / 'subject-1' / 'import-state.json').read_text().lower()
    import json
    state['medicines_imported'] = False
    (root / 'subject-1' / 'import-state.json').write_text(json.dumps(state))
    importer.load_local(root, manifest)
    assert len(db_session.scalars(select(ProfileMedicine)).all()) == 1


def test_preparation_cannot_change_dates_after_import_has_started(tmp_path):
    import json
    import pytest
    from eval.tests.test_import_mimic_demo import write_table
    root = tmp_path / 'source'
    write_table(root, 'patients', [{'subject_id': '1', 'gender': 'F'}])
    write_table(root, 'd_labitems', [{'itemid': '10', 'label': 'Creatinine', 'fluid': 'Blood'}])
    write_table(root, 'labevents', [{'subject_id': '1', 'charttime': '2180-01-01 10:00:00', 'value': '1.25', 'valuenum': '1.25', 'valueuom': 'mg/dL', 'itemid': '10'}])
    write_table(root, 'prescriptions', [{'subject_id': '1', 'drug': 'Metformin'}])
    write_table(root, 'admissions', [{'subject_id': '1', 'hadm_id': 'a'}])
    importer.prepare(root, '1', date(2026, 11, 17))
    state = root / 'subject-1' / 'import-state.json'
    state.write_text(json.dumps({'profile_id': 'already-started'}))
    with pytest.raises(ValueError, match='date|offset'):
        importer.prepare(root, '1', date(2026, 11, 18))
