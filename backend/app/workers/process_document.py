"""RQ job: turn an uploaded file into per-page text (plan 7.1). Later slices add parsing and indexing."""
import logging
import uuid
from collections.abc import Callable

import pymupdf
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.db.models import Document, DocumentPage
from app.db.session import SessionLocal
from app.services.extraction.text_layer import PageText, extract_text_layer, needs_ocr
from app.services.storage import Storage, get_storage

log = logging.getLogger(__name__)

PROCESSOR_VERSION = "extract-v1"
OCR_DPI = 200

# (png_bytes, page_no) -> PageText
OcrEngine = Callable[[bytes, int], PageText]


class ProcessingError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def process_document(document_id: str) -> None:
    """Entry point called by the RQ worker."""
    with SessionLocal() as db:
        run(db, get_storage(), uuid.UUID(document_id), ocr=None)


def run(db: Session, storage: Storage, document_id: uuid.UUID, ocr: OcrEngine | None = None) -> None:
    doc = db.get(Document, document_id)
    if doc is None:
        return  # deleted before we got to it
    doc.status, doc.error_code = "extracting", None
    db.commit()
    try:
        pages = _extract_pages(storage.get(doc.storage_key), doc.mime_type, ocr)
        db.execute(delete(DocumentPage).where(DocumentPage.document_id == doc.id))
        db.add_all(
            DocumentPage(
                document_id=doc.id,
                page_no=p.page_no,
                method=p.method,
                text=p.text,
                ocr_confidence=p.ocr_confidence,
                words_json=p.words,
                processor_version=PROCESSOR_VERSION,
            )
            for p in pages
        )
        doc.status = "done"
        db.commit()
    except Exception as e:
        db.rollback()
        code = e.code if isinstance(e, ProcessingError) else "processing_error"
        # Log ids and error type only, never document text.
        log.exception("document %s failed: %s", document_id, code)
        doc = db.get(Document, document_id)
        doc.status, doc.error_code = "failed", code
        db.commit()


def _extract_pages(data: bytes, mime: str, ocr: OcrEngine | None) -> list[PageText]:
    if mime != "application/pdf":
        if ocr is None:
            raise ProcessingError("ocr_unavailable")
        return [ocr(data, 1)]

    pages = extract_text_layer(data)
    if ocr is None:
        return pages
    with pymupdf.open(stream=data, filetype="pdf") as pdf:
        return [
            ocr(pdf[p.page_no - 1].get_pixmap(dpi=OCR_DPI).tobytes("png"), p.page_no) if needs_ocr(p) else p
            for p in pages
        ]
