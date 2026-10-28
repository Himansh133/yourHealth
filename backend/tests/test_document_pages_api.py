from app.db.models import Document, DocumentPage

PAPA = {"display_name": "Papa"}


def add_doc_with_page(db, pid):
    doc = Document(profile_id=pid, source_channel="web", storage_key="docs/x", mime_type="application/pdf",
                   size_bytes=1, sha256="x", status="done")
    db.add(doc)
    db.flush()
    db.add(DocumentPage(document_id=doc.id, page_no=1, method="rapidocr", text="HbA1c 7.2 %", ocr_confidence=0.97,
                        words_json=[{"text": "HbA1c", "x0": 1, "y0": 2, "x1": 3, "y1": 4, "conf": 0.99}],
                        processor_version="extract-v1"))
    db.commit()
    return doc


def test_get_page_text_and_words(make_user_client, db_session):
    a = make_user_client("a@example.com")
    pid = a.post("/api/v1/profiles", json=PAPA).json()["id"]
    doc = add_doc_with_page(db_session, pid)

    resp = a.get(f"/api/v1/documents/{doc.id}/pages/1")

    assert resp.status_code == 200
    assert resp.json() == {
        "page_no": 1, "method": "rapidocr", "text": "HbA1c 7.2 %", "ocr_confidence": 0.97,
        "words": [{"text": "HbA1c", "x0": 1, "y0": 2, "x1": 3, "y1": 4, "conf": 0.99}],
    }


def test_missing_page_404(make_user_client, db_session):
    a = make_user_client("a@example.com")
    pid = a.post("/api/v1/profiles", json=PAPA).json()["id"]
    doc = add_doc_with_page(db_session, pid)
    assert a.get(f"/api/v1/documents/{doc.id}/pages/2").status_code == 404


def test_other_user_cannot_read_page(make_user_client, db_session):
    a = make_user_client("a@example.com")
    b = make_user_client("b@example.com")
    pid = a.post("/api/v1/profiles", json=PAPA).json()["id"]
    doc = add_doc_with_page(db_session, pid)
    assert b.get(f"/api/v1/documents/{doc.id}/pages/1").status_code == 404
