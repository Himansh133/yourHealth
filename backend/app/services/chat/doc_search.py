"""Index document text and find the chunks that answer a question (plan 10.5, keyword half).

Keyword search with Postgres full-text ('simple' config) and an OR of the question's content words. Dense
retrieval and fusion come with the embedding model. The profile filter is part of the query itself.
"""
import re
import uuid
from dataclasses import dataclass
from datetime import date

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.db.models import Chunk, Document
from app.services.chat.chunking import CHUNKER_VERSION, chunk_pages

TOP_K = 6
DOC_TYPE_TEXT = {"lab_report": "Lab report", "prescription": "Prescription", "discharge": "Discharge summary"}

# Question words that don't say what to look for, in English and Hinglish.
STOPWORDS = set("""
a an the is are was were be been am do does did done have has had what which who whom whose when where why how
i me my we our you your he him his she her it its they them their this that these those of in on at to for from
with about by as or and but if then than so not no any some all can could would should will shall may might must
say said says tell told mention mentioned write wrote written report reports document documents doctor summary
please there here also just
kya kab kaise kaun kitna kitni ko ka ki ke mein me se par aur ya hai hain tha thi the bola boli bole kaha kahi
likha baare bare wala wali hua hui ho
""".split())


@dataclass(frozen=True)
class ChunkHit:
    document_id: uuid.UUID
    page_start: int
    page_end: int
    text: str
    doc_type: str
    title: str | None
    report_date: date | None

    def evidence_text(self) -> str:
        pages = f"p.{self.page_start}" if self.page_start == self.page_end else f"p.{self.page_start}-{self.page_end}"
        about = [DOC_TYPE_TEXT.get(self.doc_type, "Document"), self.title,
                 self.report_date.isoformat() if self.report_date else None, pages]
        return f"document | {', '.join(p for p in about if p)} | {self.text}"


def index_document(db: Session, doc: Document, pages: list[tuple[int, str]]) -> None:
    db.execute(delete(Chunk).where(Chunk.document_id == doc.id))
    db.add_all(
        Chunk(profile_id=doc.profile_id, document_id=doc.id, chunk_type=c.chunk_type, page_start=c.page_start,
              page_end=c.page_end, text=c.text, chunker_version=CHUNKER_VERSION)
        for c in chunk_pages(pages, doc.doc_type)
    )


def search_chunks(db: Session, profile_id: uuid.UUID, question: str, limit: int = TOP_K) -> list[ChunkHit]:
    terms = [w for w in re.split(r"[\W_]+", question.lower()) if len(w) > 1 and w not in STOPWORDS]
    if not terms:
        return []
    query = func.to_tsquery("simple", " | ".join(dict.fromkeys(terms)))
    rank = func.ts_rank_cd(Chunk.tsv, query)
    rows = db.execute(
        select(Chunk, Document.doc_type, func.coalesce(Document.lab_name, Document.original_filename),
               Document.report_date)
        .join(Document, Document.id == Chunk.document_id)
        .where(Chunk.profile_id == profile_id, Chunk.tsv.op("@@")(query))
        .order_by(rank.desc(), Chunk.page_start)
        .limit(limit)
    ).all()
    return [ChunkHit(c.document_id, c.page_start, c.page_end, c.text, doc_type, title, report_date)
            for c, doc_type, title, report_date in rows]
