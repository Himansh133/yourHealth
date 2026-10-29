from datetime import date

import pytest

from app.db.models import Chunk, Document
from app.services.chat.doc_search import index_document, search_chunks

PAPA = {"display_name": "Papa"}


@pytest.fixture
def pid(make_user_client):
    return make_user_client("a@example.com").post("/api/v1/profiles", json=PAPA).json()["id"]


def add_doc(db, pid, pages, doc_type="discharge", name="discharge.pdf"):
    doc = Document(profile_id=pid, source_channel="web", storage_key=f"docs/{name}", mime_type="application/pdf",
                   size_bytes=1, sha256=name, doc_type=doc_type, status="done", original_filename=name,
                   lab_name="City Hospital", report_date=date(2026, 3, 2))
    db.add(doc)
    db.flush()
    index_document(db, doc, pages)
    db.commit()
    return doc


DISCHARGE = [(1, "Diagnosis:\nType 2 diabetes mellitus with foot ulcer\nCourse in Hospital\nTreated with insulin and "
                 "dressing."), (2, "Advice on Discharge:\nLow sugar diet, walk daily for 30 minutes.\nReview in 2 weeks.")]


def test_finds_the_chunk_that_answers_with_page_and_document(db_session, pid):
    doc = add_doc(db_session, pid, DISCHARGE)
    hits = search_chunks(db_session, pid, "What did the discharge summary say about diet?")
    assert hits
    top = hits[0]
    assert "Low sugar diet" in top.text
    assert (top.document_id, top.page_start) == (doc.id, 2)
    assert top.evidence_text().startswith("document | Discharge summary, City Hospital, 2026-03-02, p.2 | ")


def test_hinglish_question_words_are_ignored(db_session, pid):
    add_doc(db_session, pid, DISCHARGE)
    hits = search_chunks(db_session, pid, "papa ko diet ke baare mein kya bola tha")
    assert hits and "Low sugar diet" in hits[0].text


def test_no_match_returns_nothing(db_session, pid):
    add_doc(db_session, pid, DISCHARGE)
    assert search_chunks(db_session, pid, "what about the knee x-ray?") == []


def test_question_of_only_common_words_returns_nothing(db_session, pid):
    add_doc(db_session, pid, DISCHARGE)
    assert search_chunks(db_session, pid, "what did it say?") == []


def test_other_profiles_documents_are_never_searched(db_session, pid, make_user_client):
    other = make_user_client("b@example.com").post("/api/v1/profiles", json=PAPA).json()["id"]
    add_doc(db_session, other, DISCHARGE)
    assert search_chunks(db_session, pid, "diet") == []


def test_reindexing_replaces_old_chunks(db_session, pid):
    doc = add_doc(db_session, pid, DISCHARGE)
    index_document(db_session, doc, [(1, "Only this now")])
    db_session.commit()
    assert [c.text for c in db_session.query(Chunk).filter_by(document_id=doc.id)] == ["Only this now"]


def test_deleting_the_document_deletes_its_chunks(db_session, pid):
    doc = add_doc(db_session, pid, DISCHARGE)
    db_session.delete(doc)
    db_session.commit()
    assert db_session.query(Chunk).count() == 0
