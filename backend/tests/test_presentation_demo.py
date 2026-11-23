import uuid
from types import SimpleNamespace

from sqlalchemy import select

from app.db.models import Document, LabResult
from app.main import app
from app.services.queue import get_queue
from app.services.storage import MemoryStorage, get_storage
from app.workers.process_document import run
from eval.runners.presentation_demo import generate_demo


def test_generated_demo_reports_go_through_real_upload_and_extraction(make_user_client, db_session, tmp_path):
    storage = MemoryStorage()
    jobs = []
    app.dependency_overrides[get_storage] = lambda: storage
    app.dependency_overrides[get_queue] = lambda: SimpleNamespace(enqueue_document=lambda did: jobs.append(did))
    user = make_user_client("presentation@example.com")
    profile = user.post("/api/v1/profiles", json={"display_name": "Demo · Sample Patient", "relation_label": "Synthetic demo data"}).json()
    for path in generate_demo(tmp_path):
        response = user.post(f"/api/v1/profiles/{profile['id']}/documents", files={"file": (path.name, path.read_bytes(), "application/pdf")})
        assert response.status_code == 201
        did = uuid.UUID(response.json()["id"])
        run(db_session, storage, did)
        doc = db_session.get(Document, did)
        assert doc.status in ("done", "needs_review")
        assert doc.doc_type == "lab_report"
        assert doc.report_date.isoformat() in path.name
        rows = db_session.scalars(select(LabResult).where(LabResult.document_id == did)).all()
        assert len(rows) == 3
        assert all(r.lab_test_id and r.value_canonical is not None for r in rows)
    assert len(jobs) == 3
    trends = user.get(f"/api/v1/profiles/{profile['id']}/trends").json()
    assert len(trends) == 3
    hba1c = next(t for t in trends if t["test"]["loinc_code"] == "4548-4")
    assert [p["value"] for p in hba1c["points"]] == [8.1, 7.6, 7.2]
