import uuid

from app.db.models import ProfileMember, User


def test_patient_allergies_start_unknown_and_are_scoped(make_user_client):
    owner = make_user_client('allergy-owner@example.com')
    other = make_user_client('allergy-other@example.com')
    pid = owner.post('/api/v1/profiles', json={'display_name': 'Demo'}).json()['id']
    path = f'/api/v1/profiles/{pid}/allergies'
    response = owner.get(path)
    assert response.status_code == 200
    assert response.json() == {'status': 'unknown', 'confirmed_at': None, 'entries': []}
    assert other.get(path).status_code == 404
    assert other.post(path, json={'substance_text': 'Peanut'}).status_code == 404


def test_viewer_can_read_but_cannot_add_allergies(make_user_client, db_session):
    owner = make_user_client('allergy-owner@example.com')
    viewer = make_user_client('allergy-viewer@example.com')
    pid = owner.post('/api/v1/profiles', json={'display_name': 'Demo'}).json()['id']
    uid = viewer.get('/api/v1/me').json()['id']
    db_session.add(ProfileMember(profile_id=uuid.UUID(pid), user_id=uuid.UUID(uid), role='viewer'))
    db_session.commit()
    path = f'/api/v1/profiles/{pid}/allergies'
    assert viewer.get(path).status_code == 200
    assert viewer.post(path, json={'substance_text': 'Peanut'}).status_code == 403


def test_doctor_cannot_use_patient_allergy_endpoint(make_user_client, db_session):
    doctor = make_user_client('allergy-doctor@example.com')
    uid = uuid.UUID(doctor.get('/api/v1/me').json()['id'])
    db_session.get(User, uid).account_type = 'doctor'
    db_session.commit()
    assert doctor.get(f'/api/v1/profiles/{uuid.uuid4()}/allergies').status_code == 403
