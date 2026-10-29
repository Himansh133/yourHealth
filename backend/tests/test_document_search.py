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


# --- meaning-based search and reranking (plan 10.5) -----------------------------------------------------------

class StubEmbedder:
    """Vectors chosen by the test: texts mentioning a topic word point the same way."""
    name = "stub"
    dim = 1024
    TOPICS = {"diet": 0, "food": 0, "eat": 0, "insulin": 1, "foot": 2}

    def embed(self, texts):
        out = []
        for t in texts:
            v = [0.0] * self.dim
            for word, axis in self.TOPICS.items():
                if word in t.lower():
                    v[axis] = 1.0
            v[1023] = 0.01  # never all zeros
            out.append(v)
        return out


class StubReranker:
    def __init__(self, keep_word):
        self.keep_word = keep_word

    def score(self, query, passages):
        return [0.9 if self.keep_word in p.lower() else 0.01 for p in passages]


def add_doc_with_models(db, pid, pages, embedder):
    doc = Document(profile_id=pid, source_channel="web", storage_key="docs/m", mime_type="application/pdf",
                   size_bytes=1, sha256="m", doc_type="discharge", status="done", lab_name="City Hospital")
    db.add(doc)
    db.flush()
    index_document(db, doc, pages, embedder=embedder)
    db.commit()
    return doc


def test_chunks_are_embedded_when_a_model_is_available(db_session, pid):
    doc = add_doc_with_models(db_session, pid, DISCHARGE, StubEmbedder())
    chunks = db_session.query(Chunk).filter_by(document_id=doc.id).all()
    assert all(c.embedding is not None and len(c.embedding) == 1024 for c in chunks)
    assert {c.embed_model for c in chunks} == {"stub"}


def test_meaning_finds_what_keywords_miss(db_session, pid):
    add_doc_with_models(db_session, pid, DISCHARGE, StubEmbedder())
    # "food" is not in the document; "diet" is
    assert search_chunks(db_session, pid, "what food is allowed?") == []
    hits = search_chunks(db_session, pid, "what food is allowed?", embedder=StubEmbedder())
    assert hits and "Low sugar diet" in hits[0].text


def test_reranker_puts_the_most_relevant_chunk_first(db_session, pid):
    add_doc_with_models(db_session, pid, DISCHARGE, StubEmbedder())
    hits = search_chunks(db_session, pid, "what food is allowed?", embedder=StubEmbedder(),
                         reranker=StubReranker("walk daily"))
    assert "walk daily" in hits[0].text


def test_reranker_ties_keep_the_fused_order(db_session, pid):
    # bge-reranker-v2-m3 gives every passage the same floor score for questions it can't read (e.g. Hinglish)
    class Flat:
        def score(self, query, passages):
            return [0.0] * len(passages)

    add_doc_with_models(db_session, pid, DISCHARGE, StubEmbedder())
    fused = search_chunks(db_session, pid, "what food is allowed?", embedder=StubEmbedder())
    reranked = search_chunks(db_session, pid, "what food is allowed?", embedder=StubEmbedder(), reranker=Flat())
    assert [h.text for h in reranked] == [h.text for h in fused]


def test_dense_search_never_crosses_profiles(db_session, pid, make_user_client):
    other = make_user_client("b@example.com").post("/api/v1/profiles", json=PAPA).json()["id"]
    add_doc_with_models(db_session, other, DISCHARGE, StubEmbedder())
    assert search_chunks(db_session, pid, "food", embedder=StubEmbedder()) == []
