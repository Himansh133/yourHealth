"""Index document text and find the chunks that answer a question (plan 10.5).

Two searches, fused with reciprocal rank fusion, then reordered by the reranker:
- keyword: Postgres full-text ('simple' config), an OR of the question's content words
- meaning: cosine distance between bge-m3 vectors (skipped when the model isn't installed)
The profile filter is part of both queries, before any ranking.
"""
import re
import uuid
from dataclasses import dataclass
from datetime import date

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.db.models import Chunk, Document
from app.services.chat.chunking import CHUNKER_VERSION, chunk_pages
from app.services.chat.embeddings import Embedder, Reranker

TOP_K = 6
CANDIDATES = 30  # from each search
RERANK_TOP = 20
RRF_K = 60
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


def index_document(db: Session, doc: Document, pages: list[tuple[int, str]], embedder: Embedder | None = None) -> None:
    db.execute(delete(Chunk).where(Chunk.document_id == doc.id))
    specs = chunk_pages(pages, doc.doc_type)
    vectors = embedder.embed([c.text for c in specs]) if embedder and specs else [None] * len(specs)
    db.add_all(
        Chunk(profile_id=doc.profile_id, document_id=doc.id, chunk_type=c.chunk_type, page_start=c.page_start,
              page_end=c.page_end, text=c.text, chunker_version=CHUNKER_VERSION, embedding=v,
              embed_model=embedder.name if embedder else None)
        for c, v in zip(specs, vectors)
    )


def rrf(rankings: list[list], k: int = RRF_K) -> list:
    """Reciprocal rank fusion: score(d) = sum of 1 / (k + rank) over the lists d appears in."""
    scores: dict = {}
    for ranking in rankings:
        for rank, item in enumerate(ranking, 1):
            scores[item] = scores.get(item, 0) + 1 / (k + rank)
    return sorted(scores, key=lambda item: -scores[item])


def search_chunks(db: Session, profile_id: uuid.UUID, question: str, limit: int = TOP_K,
                  embedder: Embedder | None = None, reranker: Reranker | None = None) -> list[ChunkHit]:
    keyword = _keyword_ids(db, profile_id, question)
    dense = _dense_ids(db, profile_id, embedder.embed([question])[0]) if embedder else []
    order = rrf([keyword, dense])[:RERANK_TOP if reranker else limit]
    if not order:
        return []

    rows = {c.id: (c, doc_type, title, report_date) for c, doc_type, title, report_date in db.execute(
        select(Chunk, Document.doc_type, func.coalesce(Document.lab_name, Document.original_filename),
               Document.report_date)
        .join(Document, Document.id == Chunk.document_id)
        .where(Chunk.profile_id == profile_id, Chunk.id.in_(order))
    ).all()}
    hits = [_hit(*rows[i]) for i in order]
    if reranker:
        # Order only, no cut-off: on medical text its scores are low even for the right passage, and an unrelated
        # question can score as high (measured). Whether the passages answer the question is the LLM's call.
        # Stable sort: equal scores keep the fused order.
        scores = reranker.score(question, [h.text for h in hits])
        hits = [h for _, h in sorted(zip(scores, hits), key=lambda sh: -sh[0])]
    return hits[:limit]


def _keyword_ids(db: Session, profile_id: uuid.UUID, question: str) -> list[uuid.UUID]:
    terms = [w for w in re.split(r"[\W_]+", question.lower()) if len(w) > 1 and w not in STOPWORDS]
    if not terms:
        return []
    query = func.to_tsquery("simple", " | ".join(dict.fromkeys(terms)))
    return list(db.scalars(
        select(Chunk.id)
        .where(Chunk.profile_id == profile_id, Chunk.tsv.op("@@")(query))
        .order_by(func.ts_rank_cd(Chunk.tsv, query).desc(), Chunk.page_start)
        .limit(CANDIDATES)
    ))


def _dense_ids(db: Session, profile_id: uuid.UUID, vector: list[float]) -> list[uuid.UUID]:
    return list(db.scalars(
        select(Chunk.id)
        .where(Chunk.profile_id == profile_id, Chunk.embedding.is_not(None))
        .order_by(Chunk.embedding.cosine_distance(vector))
        .limit(CANDIDATES)
    ))


def _hit(c: Chunk, doc_type: str, title: str | None, report_date: date | None) -> ChunkHit:
    return ChunkHit(c.document_id, c.page_start, c.page_end, c.text, doc_type, title, report_date)
