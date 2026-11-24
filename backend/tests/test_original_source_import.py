import uuid

import pytest

from sqlalchemy import select, func
from sqlalchemy.orm import sessionmaker

from app.db.models import Document, LabResult, Profile, ProfileMember, ProfileMedicine, User
from app.services.storage import MemoryStorage, get_storage
from eval.runners.import_original_source import load_originals


def test_original_import_preserves_sources_is_private_and_resumes(tmp_path, db_session, make_user_client, monkeypatch):
    owner = make_user_client('demo-check@example.com')
    other = make_user_client('other@example.com')
    old_id = owner.post('/api/v1/profiles', json={'display_name': 'Demo - MIMIC 1'}).json()['id']
    source = tmp_path / 'source'
    source.mkdir()
    sources = {
        'patients': 'subject_id,gender\n1,F\n2,M\n',
        'admissions': 'subject_id,admittime\n1,2159-08-01 00:00:00\n2,2150-01-01 00:00:00\n',
        'd_labitems': 'itemid,label,fluid\n10,Creatinine,Blood\n11,Creatinine,Urine\n',
        'labevents': 'subject_id,labevent_id,itemid,charttime,value,valueuom,ref_range_lower,ref_range_upper\n1,42,10,2159-08-03 10:30:00,2.10,mg/dL,0.5,1.2\n1,43,11,2159-08-03 10:30:00,3.00,mg/dL,,\n2,44,10,2159-08-03 10:30:00,99,mg/dL,,\n',
        'prescriptions': 'subject_id,drug,dose_val_rx,dose_unit_rx,route,starttime,stoptime\n1,Aspirin,81,mg,PO,2159-08-01 00:00:00,2159-08-02 00:00:00\n2,Other,1,mg,PO,,\n',
    }
    for table, text in sources.items():
        (source / f'{table}.csv').write_text(text)
    storage = MemoryStorage()
    monkeypatch.setattr('app.services.storage.get_storage', lambda: storage)
    monkeypatch.setattr('app.db.session.SessionLocal', sessionmaker(bind=db_session.get_bind()))
    from app.main import app
    app.dependency_overrides[get_storage] = lambda: storage
    target = tmp_path / 'selected'
    with pytest.raises(ValueError, match='Archive switch'):
        load_originals(source, target, '1', 'demo-check@example.com', switch_from=old_id)
    user_id = db_session.scalar(select(User.id).where(User.email == 'demo-check@example.com'))
    db_session.get(ProfileMember, (uuid.UUID(old_id), user_id)).relation_label = 'De-identified demo data'
    seed = User(email='demo.mimic.fixture@example.com', password_hash='not-a-password')
    db_session.add(seed)
    db_session.flush()
    db_session.add(ProfileMember(profile_id=uuid.UUID(old_id), user_id=seed.id, role='owner', relation_label='De-identified demo data'))
    db_session.commit()
    state = load_originals(source, target, '1', 'demo-check@example.com', switch_from=old_id)
    pid = uuid.UUID(state['profile_id'])
    assert state['lab_rows'] == 2 and state['prescriptions'] == 1
    assert load_originals(source, target, '1', 'demo-check@example.com', switch_from=old_id)['profile_id'] == str(pid)
    assert db_session.scalar(select(func.count()).select_from(Document).where(Document.profile_id == pid)) == 5
    labs = list(db_session.scalars(select(LabResult).where(LabResult.profile_id == pid).order_by(LabResult.raw_value)))
    assert [r.raw_value for r in labs] == ['2.10', '3.00']
    assert labs[0].observed_on.isoformat() == '2159-08-03'
    assert labs[0].lab_test_id and labs[1].lab_test_id is None
    assert all(r.page_no is None for r in labs)
    med = db_session.scalar(select(ProfileMedicine).where(ProfileMedicine.profile_id == pid))
    assert not med.confirmed_by_user and med.started_on.isoformat() == '2159-08-01'
    assert db_session.get(Profile, uuid.UUID(old_id)) is not None
    user_id = db_session.scalar(select(User.id).where(User.email == 'demo-check@example.com'))
    assert db_session.get(ProfileMember, (uuid.UUID(old_id), user_id)) is None
    for doc in db_session.scalars(select(Document).where(Document.profile_id == pid)):
        assert doc.mime_type == 'text/csv'
        assert storage.get(doc.storage_key) == (target / doc.original_filename).read_bytes()
        assert owner.get(f'/api/v1/documents/{doc.id}/file').status_code == 200
        assert other.get(f'/api/v1/documents/{doc.id}/file').status_code == 404
    assert all((source / f'{table}.csv').read_text() == text for table, text in sources.items())
