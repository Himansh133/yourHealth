PAPA = {"display_name": "Papa", "birth_year": 1968, "sex": "male", "relation_label": "father"}


def test_create_profile_makes_creator_owner(make_user_client):
    a = make_user_client("a@example.com")
    resp = a.post("/api/v1/profiles", json=PAPA)
    assert resp.status_code == 201
    body = resp.json()
    assert body["display_name"] == "Papa"
    assert body["role"] == "owner"
    assert body["relation_label"] == "father"


def test_list_profiles_shows_only_mine(make_user_client):
    a = make_user_client("a@example.com")
    b = make_user_client("b@example.com")
    a.post("/api/v1/profiles", json=PAPA)
    b.post("/api/v1/profiles", json={**PAPA, "display_name": "B's Papa"})

    names = [p["display_name"] for p in a.get("/api/v1/profiles").json()]
    assert names == ["Papa"]


def test_patch_profile(make_user_client):
    a = make_user_client("a@example.com")
    pid = a.post("/api/v1/profiles", json=PAPA).json()["id"]
    resp = a.patch(f"/api/v1/profiles/{pid}", json={"display_name": "Pitaji"})
    assert resp.status_code == 200
    assert resp.json()["display_name"] == "Pitaji"
    assert resp.json()["birth_year"] == 1968


def test_delete_profile(make_user_client):
    a = make_user_client("a@example.com")
    pid = a.post("/api/v1/profiles", json=PAPA).json()["id"]
    assert a.delete(f"/api/v1/profiles/{pid}").status_code == 204
    assert a.get("/api/v1/profiles").json() == []


def test_invalid_sex_rejected(make_user_client):
    a = make_user_client("a@example.com")
    assert a.post("/api/v1/profiles", json={**PAPA, "sex": "robot"}).status_code == 422


def test_profiles_require_login(client):
    assert client.get("/api/v1/profiles").status_code == 401


# --- isolation (plan 12.3): other users' profiles look like they don't exist ---

def test_other_user_cannot_patch_profile(make_user_client):
    a = make_user_client("a@example.com")
    b = make_user_client("b@example.com")
    pid = a.post("/api/v1/profiles", json=PAPA).json()["id"]
    assert b.patch(f"/api/v1/profiles/{pid}", json={"display_name": "hacked"}).status_code == 404


def test_other_user_cannot_delete_profile(make_user_client):
    a = make_user_client("a@example.com")
    b = make_user_client("b@example.com")
    pid = a.post("/api/v1/profiles", json=PAPA).json()["id"]
    assert b.delete(f"/api/v1/profiles/{pid}").status_code == 404
    assert len(a.get("/api/v1/profiles").json()) == 1


def test_unknown_profile_id_404(make_user_client):
    a = make_user_client("a@example.com")
    resp = a.patch("/api/v1/profiles/00000000-0000-0000-0000-000000000000", json={"display_name": "x"})
    assert resp.status_code == 404


def test_caregiver_can_edit_but_not_delete(make_user_client, db_session):
    from app.db.models import ProfileMember, User

    a = make_user_client("a@example.com")
    b = make_user_client("b@example.com")
    pid = a.post("/api/v1/profiles", json=PAPA).json()["id"]
    b_user = db_session.query(User).filter_by(email="b@example.com").one()
    db_session.add(ProfileMember(profile_id=pid, user_id=b_user.id, role="caregiver"))
    db_session.commit()

    assert b.patch(f"/api/v1/profiles/{pid}", json={"display_name": "Pitaji"}).status_code == 200
    assert b.delete(f"/api/v1/profiles/{pid}").status_code == 403
