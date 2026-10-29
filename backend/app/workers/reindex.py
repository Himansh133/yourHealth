"""Rebuild search chunks (and their embeddings) from stored page text: after changing the chunker or the
embedding model, or for documents processed before either existed. Usage: python -m app.workers.reindex"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Document, DocumentPage
from app.db.session import SessionLocal
from app.services.chat.doc_search import index_document
from app.services.chat.embeddings import get_embedder


def reindex_all(db: Session) -> int:
    embedder = get_embedder()
    count = 0
    for doc in db.scalars(select(Document).where(Document.status.in_(["done", "needs_review"]))):
        pages = db.execute(select(DocumentPage.page_no, DocumentPage.text)
                           .where(DocumentPage.document_id == doc.id).order_by(DocumentPage.page_no)).all()
        index_document(db, doc, [(no, text) for no, text in pages], embedder=embedder)
        db.commit()
        count += 1
    return count


if __name__ == "__main__":
    with SessionLocal() as db:
        print(f"reindexed {reindex_all(db)} documents")
