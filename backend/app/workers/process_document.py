"""RQ job: uploaded file -> page text -> lab results (plan 7.1). Indexing comes in a later slice."""
import logging
import uuid
from collections.abc import Callable

import pymupdf
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.db.models import Document, DocumentPage, LabResult, LabTestRecord
from app.db.session import SessionLocal
from app.services.extraction.classify import classify_document, find_lab_name, find_report_date
from app.services.extraction.ocr import rapid_ocr
from app.services.extraction.text_layer import PageText, extract_text_layer, needs_ocr
from app.services.labs.dictionary import LabDictionary, get_lab_dictionary
from app.services.labs.normalize import REVIEW_BELOW, normalize_row
from app.services.labs.row_parser import parse_words
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
        run(db, get_storage(), uuid.UUID(document_id), ocr=rapid_ocr)


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
        doc.status = "parsing"
        _store_lab_results(db, doc, pages, get_lab_dictionary())
        db.commit()
    except Exception as e:
        db.rollback()
        code = e.code if isinstance(e, ProcessingError) else "processing_error"
        # Log ids and error type only, never document text.
        log.exception("document %s failed: %s", document_id, code)
        doc = db.get(Document, document_id)
        doc.status, doc.error_code = "failed", code
        db.commit()


def _store_lab_results(db: Session, doc: Document, pages: list[PageText], d: LabDictionary) -> None:
    rows = [(p.page_no, normalize_row(r, d, p.ocr_confidence)) for p in pages for r in parse_words(p.words)]
    text = "\n".join(p.text for p in pages)
    doc.doc_type = classify_document(text, len(rows))
    doc.lab_name = find_lab_name(text)
    doc.report_date = find_report_date(text)
    db.execute(delete(LabResult).where(LabResult.document_id == doc.id))
    if doc.doc_type != "lab_report":
        doc.status = "done"
        return

    test_ids = _lab_test_ids(db, d)
    # Without a printed date we still store the rows, but a human must confirm the date.
    observed_on = doc.report_date or doc.created_at.date()
    db.add_all(
        LabResult(
            profile_id=doc.profile_id,
            document_id=doc.id,
            lab_test_id=test_ids[n.test.loinc_code] if n.test else None,
            raw_name=n.raw.raw_name,
            raw_value=n.raw.raw_value,
            raw_unit=n.raw.raw_unit,
            raw_range=n.raw.raw_range,
            printed_flag=n.raw.printed_flag,
            value_num=n.value_num,
            value_canonical=n.value_canonical,
            qualifier=n.qualifier,
            range_low=n.range_low,
            range_high=n.range_high,
            range_low_canonical=n.range_low_canonical,
            range_high_canonical=n.range_high_canonical,
            flag=n.flag,
            observed_on=observed_on,
            page_no=page_no,
            bbox=n.raw.bbox,
            extraction_method="regex",
            extraction_confidence=n.confidence,
        )
        for page_no, n in rows
    )
    low_confidence = any(n.confidence < REVIEW_BELOW for _, n in rows)
    doc.status = "needs_review" if low_confidence or doc.report_date is None else "done"


def _lab_test_ids(db: Session, d: LabDictionary) -> dict[str, uuid.UUID]:
    """Make sure every dictionary test has a lab_tests row; return loinc_code -> id."""
    db.execute(
        insert(LabTestRecord)
        .values([
            {"id": uuid.uuid4(), "loinc_code": t.loinc_code, "canonical_name": t.canonical_name,
             "display_name_hi": t.display_name_hi, "canonical_unit": t.canonical_unit, "category": t.category}
            for t in d.tests.values()
        ])
        .on_conflict_do_nothing(index_elements=["loinc_code"])
    )
    return dict(db.execute(select(LabTestRecord.loinc_code, LabTestRecord.id)).all())


def _extract_pages(data: bytes, mime: str, ocr: OcrEngine | None) -> list[PageText]:
    if mime != "application/pdf":
        if ocr is None:
            raise ProcessingError("ocr_unavailable")
        return [ocr(data, 1)]

    pages = extract_text_layer(data)
    if ocr is None:
        return pages
    with pymupdf.open(stream=data, filetype="pdf") as pdf:
        return [_ocr_pdf_page(pdf, p.page_no, ocr) if needs_ocr(p) else p for p in pages]


def _ocr_pdf_page(pdf, page_no: int, ocr: OcrEngine) -> PageText:
    page = ocr(pdf[page_no - 1].get_pixmap(dpi=OCR_DPI).tobytes("png"), page_no)
    # OCR boxes are in rendered pixels; store PDF points so they match text-layer boxes.
    scale = 72 / OCR_DPI
    for w in page.words:
        for k in ("x0", "y0", "x1", "y1"):
            w[k] = round(w[k] * scale, 1)
    return page
