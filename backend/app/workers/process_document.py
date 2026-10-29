"""RQ job: uploaded file -> page text -> lab results and medicines -> search chunks (plan 7.1)."""
import logging
import uuid
from collections.abc import Callable

import pymupdf
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models import Document, DocumentPage, DrugBrand, DrugBrandIngredient, LabResult, ProfileMedicine
from app.db.session import SessionLocal
from app.services.chat.doc_search import index_document
from app.services.chat.embeddings import get_embedder
from app.services.extraction.classify import classify_document, find_lab_name, find_report_date
from app.services.extraction.ocr import group_rows, rapid_ocr
from app.services.extraction.text_layer import PageText, extract_text_layer, needs_ocr
from app.services.labs.dictionary import LabDictionary, get_lab_dictionary
from app.services.labs.normalize import REVIEW_BELOW, normalize_row
from app.services.labs.row_parser import parse_words
from app.services.labs.store import lab_test_ids, normalized_fields
from app.services.medicines.brands import BrandIndex
from app.services.medicines.prescription import parse_prescription_line
from app.services.medicines.store import set_ingredients
from app.services.storage import Storage, get_storage
from app.services.whatsapp.client import get_whatsapp
from app.services.whatsapp.handler import notify_report_done

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
        try:
            notify_report_done(db, get_whatsapp(), uuid.UUID(document_id))
        except Exception:  # the report is processed either way; a failed reply mustn't fail the job
            log.exception("WhatsApp reply for document %s failed", document_id)


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
        index_document(db, doc, [(p.page_no, p.text) for p in pages], embedder=get_embedder())
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
    doc.doc_type = classify_document(text, len(rows), sum(1 for _, n in rows if n.test))
    doc.lab_name = find_lab_name(text)
    doc.report_date = find_report_date(text)
    db.execute(delete(LabResult).where(LabResult.document_id == doc.id))
    if doc.doc_type == "prescription":
        _store_prescription(db, doc, pages)
    if doc.doc_type != "lab_report":
        doc.status = "done"
        return

    test_ids = lab_test_ids(db, d)
    # Without a printed date we still store the rows, but a human must confirm the date.
    observed_on = doc.report_date or doc.created_at.date()
    db.add_all(
        LabResult(
            profile_id=doc.profile_id,
            document_id=doc.id,
            observed_on=observed_on,
            page_no=page_no,
            bbox=n.raw.bbox,
            extraction_method="regex",
            **normalized_fields(n, test_ids),
        )
        for page_no, n in rows
    )
    low_confidence = any(n.confidence < REVIEW_BELOW for _, n in rows)
    doc.status = "needs_review" if low_confidence or doc.report_date is None else "done"


def _store_prescription(db: Session, doc: Document, pages: list[PageText]) -> None:
    """Medicine lines become unconfirmed medicines (plan 9.1); nothing counts until the user confirms."""
    db.execute(delete(ProfileMedicine).where(ProfileMedicine.source_document_id == doc.id,
                                             ProfileMedicine.confirmed_by_user.is_(False)))
    confirmed = set(db.scalars(select(ProfileMedicine.raw_text).where(ProfileMedicine.source_document_id == doc.id)))
    brands = {b.brand_name: b for b in db.scalars(select(DrugBrand))}
    index = BrandIndex.from_rows([(b.brand_name, b.composition_raw, b.source) for b in brands.values()])

    for page in pages:
        for row in group_rows(page.words):
            line = " ".join(w["text"] for w in row)
            rx = parse_prescription_line(line)
            if rx is None or line in confirmed:
                continue
            match = index.match(rx.brand_text)
            brand = brands[match.brand_name] if match else None
            med = ProfileMedicine(profile_id=doc.profile_id, brand_id=brand.id if brand else None, raw_text=line,
                                  frequency_code=rx.frequency_code, source_document_id=doc.id, confirmed_by_user=False)
            db.add(med)
            db.flush()
            if brand:
                set_ingredients(db, med, list(db.scalars(
                    select(DrugBrandIngredient.ingredient_id).where(DrugBrandIngredient.brand_id == brand.id))))


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
