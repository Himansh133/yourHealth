import pymupdf
import pytest

from app.main import app
from app.services.queue import get_queue
from app.services.storage import MemoryStorage, get_storage

PAPA = {"display_name": "Papa", "birth_year": 1968, "sex": "male"}


def make_pdf(text="HbA1c 7.2 % 4.0 - 5.6") -> bytes:
    doc = pymupdf.open()
    doc.new_page().insert_text((72, 72), text)
    return doc.tobytes()


class FakeQueue:
    def __init__(self):
        self.jobs = []

    def enqueue_document(self, document_id):
        self.jobs.append(str(document_id))


@pytest.fixture
def queue():
    q = FakeQueue()
    app.dependency_overrides[get_queue] = lambda: q
    return q


@pytest.fixture
def storage(queue):
    s = MemoryStorage()
    app.dependency_overrides[get_storage] = lambda: s
    yield s


def upload(c, pid, data, name="report.pdf", ctype="application/pdf"):
    return c.post(f"/api/v1/profiles/{pid}/documents", files={"file": (name, data, ctype)})


def test_upload_pdf_creates_queued_document_and_stores_file(make_user_client, storage):
    a = make_user_client("a@example.com")
    pid = a.post("/api/v1/profiles", json=PAPA).json()["id"]
    pdf = make_pdf()

    resp = upload(a, pid, pdf)

    assert resp.status_code == 201
    doc = resp.json()
    assert doc["status"] == "queued"
    assert doc["mime_type"] == "application/pdf"
    assert doc["size_bytes"] == len(pdf)
    assert doc["original_filename"] == "report.pdf"
    assert doc["source_channel"] == "web"
    assert list(storage.objects.values()) == [pdf]


def test_mime_comes_from_bytes_not_client_header(make_user_client, storage):
    a = make_user_client("a@example.com")
    pid = a.post("/api/v1/profiles", json=PAPA).json()["id"]
    resp = upload(a, pid, make_pdf(), name="photo.jpg", ctype="image/jpeg")
    assert resp.json()["mime_type"] == "application/pdf"


def test_rejected_upload_returns_code_and_stores_nothing(make_user_client, storage):
    a = make_user_client("a@example.com")
    pid = a.post("/api/v1/profiles", json=PAPA).json()["id"]
    resp = upload(a, pid, b"MZ not a pdf")
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "unsupported_type"
    assert storage.objects == {}


def test_duplicate_upload_same_profile_returns_existing(make_user_client, storage):
    a = make_user_client("a@example.com")
    pid = a.post("/api/v1/profiles", json=PAPA).json()["id"]
    pdf = make_pdf()
    first = upload(a, pid, pdf).json()

    resp = upload(a, pid, pdf, name="again.pdf")

    assert resp.status_code == 200
    assert resp.json()["id"] == first["id"]
    assert len(storage.objects) == 1


def test_same_file_for_two_profiles_is_two_documents(make_user_client, storage):
    a = make_user_client("a@example.com")
    papa = a.post("/api/v1/profiles", json=PAPA).json()["id"]
    mummy = a.post("/api/v1/profiles", json={**PAPA, "display_name": "Mummy"}).json()["id"]
    pdf = make_pdf()
    assert upload(a, papa, pdf).status_code == 201
    assert upload(a, mummy, pdf).status_code == 201


def test_list_documents_for_profile(make_user_client, storage):
    a = make_user_client("a@example.com")
    pid = a.post("/api/v1/profiles", json=PAPA).json()["id"]
    upload(a, pid, make_pdf("one"))
    upload(a, pid, make_pdf("two"))
    assert len(a.get(f"/api/v1/profiles/{pid}/documents").json()) == 2


def test_get_document_and_download_original(make_user_client, storage):
    a = make_user_client("a@example.com")
    pid = a.post("/api/v1/profiles", json=PAPA).json()["id"]
    pdf = make_pdf()
    did = upload(a, pid, pdf).json()["id"]

    assert a.get(f"/api/v1/documents/{did}").json()["id"] == did
    file_resp = a.get(f"/api/v1/documents/{did}/file")
    assert file_resp.status_code == 200
    assert file_resp.content == pdf
    assert file_resp.headers["content-type"] == "application/pdf"


def test_delete_document_removes_row_and_file(make_user_client, storage):
    a = make_user_client("a@example.com")
    pid = a.post("/api/v1/profiles", json=PAPA).json()["id"]
    did = upload(a, pid, make_pdf()).json()["id"]

    assert a.delete(f"/api/v1/documents/{did}").status_code == 204
    assert a.get(f"/api/v1/documents/{did}").status_code == 404
    assert storage.objects == {}


# --- isolation (plan 12.3) ---------------------------------------------------

def test_other_user_cannot_upload_to_my_profile(make_user_client, storage):
    a = make_user_client("a@example.com")
    b = make_user_client("b@example.com")
    pid = a.post("/api/v1/profiles", json=PAPA).json()["id"]
    assert upload(b, pid, make_pdf()).status_code == 404
    assert storage.objects == {}


def test_missing_stored_file_is_not_found_not_a_server_error(make_user_client, storage):
    a = make_user_client("a@example.com")
    pid = a.post("/api/v1/profiles", json=PAPA).json()["id"]
    did = upload(a, pid, make_pdf()).json()["id"]
    storage.objects.clear()

    resp = a.get(f"/api/v1/documents/{did}/file")

    assert resp.status_code == 404
    assert resp.json()["detail"] == "The original file is missing"


def test_other_user_cannot_list_read_download_or_delete(make_user_client, storage):
    a = make_user_client("a@example.com")
    b = make_user_client("b@example.com")
    pid = a.post("/api/v1/profiles", json=PAPA).json()["id"]
    did = upload(a, pid, make_pdf()).json()["id"]

    assert b.get(f"/api/v1/profiles/{pid}/documents").status_code == 404
    assert b.get(f"/api/v1/documents/{did}").status_code == 404
    assert b.get(f"/api/v1/documents/{did}/file").status_code == 404
    assert b.delete(f"/api/v1/documents/{did}").status_code == 404
    assert a.get(f"/api/v1/documents/{did}").status_code == 200


def test_viewer_can_download_but_not_upload_or_delete(make_user_client, db_session, storage):
    from app.db.models import ProfileMember, User

    a = make_user_client("a@example.com")
    v = make_user_client("v@example.com")
    pid = a.post("/api/v1/profiles", json=PAPA).json()["id"]
    did = upload(a, pid, make_pdf()).json()["id"]
    v_user = db_session.query(User).filter_by(email="v@example.com").one()
    db_session.add(ProfileMember(profile_id=pid, user_id=v_user.id, role="viewer"))
    db_session.commit()

    assert v.get(f"/api/v1/documents/{did}/file").status_code == 200
    assert upload(v, pid, make_pdf("other")).status_code == 403
    assert v.delete(f"/api/v1/documents/{did}").status_code == 403


def test_deleting_profile_removes_its_files(make_user_client, storage):
    a = make_user_client("a@example.com")
    pid = a.post("/api/v1/profiles", json=PAPA).json()["id"]
    upload(a, pid, make_pdf())
    assert a.delete(f"/api/v1/profiles/{pid}").status_code == 204
    assert storage.objects == {}


def test_new_upload_enqueues_processing_job(make_user_client, storage, queue):
    a = make_user_client("a@example.com")
    pid = a.post("/api/v1/profiles", json=PAPA).json()["id"]
    did = upload(a, pid, make_pdf()).json()["id"]
    assert queue.jobs == [did]


def test_duplicate_upload_does_not_enqueue_again(make_user_client, storage, queue):
    a = make_user_client("a@example.com")
    pid = a.post("/api/v1/profiles", json=PAPA).json()["id"]
    pdf = make_pdf()
    upload(a, pid, pdf)
    upload(a, pid, pdf)
    assert len(queue.jobs) == 1


def test_rejected_upload_does_not_enqueue(make_user_client, storage, queue):
    a = make_user_client("a@example.com")
    pid = a.post("/api/v1/profiles", json=PAPA).json()["id"]
    upload(a, pid, b"MZ not a pdf")
    assert queue.jobs == []
