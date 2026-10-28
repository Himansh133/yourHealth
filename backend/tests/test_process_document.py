import hashlib

import pymupdf
import pytest

from app.db.models import Document, DocumentPage, Profile
from app.services.extraction.text_layer import PageText
from app.services.storage import MemoryStorage
from app.workers.process_document import run

LAB_LINES = [f"Test{i} {i}.5 mg/dL 1.0 - 9.0 extra words here" for i in range(6)]


def make_pdf(pages: list[list[str]]) -> bytes:
    doc = pymupdf.open()
    for lines in pages:
        page = doc.new_page()
        for i, line in enumerate(lines):
            page.insert_text((40, 60 + i * 18), line, fontsize=9)
    return doc.tobytes()


def add_document(db, storage, data: bytes, mime="application/pdf") -> Document:
    profile = Profile(display_name="Papa")
    db.add(profile)
    db.flush()
    doc = Document(
        profile_id=profile.id,
        source_channel="web",
        storage_key=f"docs/{hashlib.sha256(data).hexdigest()}",
        mime_type=mime,
        size_bytes=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
    )
    db.add(doc)
    db.commit()
    storage.put(doc.storage_key, data, mime)
    return doc


def pages_of(db, doc):
    return db.query(DocumentPage).filter_by(document_id=doc.id).order_by(DocumentPage.page_no).all()


def test_digital_pdf_pages_are_stored_and_document_done(db_session):
    storage = MemoryStorage()
    doc = add_document(db_session, storage, make_pdf([LAB_LINES, LAB_LINES]))

    run(db_session, storage, doc.id)

    db_session.refresh(doc)
    assert doc.status == "done"
    pages = pages_of(db_session, doc)
    assert [p.page_no for p in pages] == [1, 2]
    assert pages[0].method == "text_layer"
    assert "Test3" in pages[0].text
    assert pages[0].words_json[0]["text"] == "Test0"
    assert pages[0].processor_version


def test_rerun_replaces_pages_instead_of_duplicating(db_session):
    storage = MemoryStorage()
    doc = add_document(db_session, storage, make_pdf([LAB_LINES]))
    run(db_session, storage, doc.id)
    run(db_session, storage, doc.id)
    assert len(pages_of(db_session, doc)) == 1


def test_page_needing_ocr_uses_ocr_engine(db_session):
    storage = MemoryStorage()
    doc = add_document(db_session, storage, make_pdf([LAB_LINES, ["Scanned page"]]))
    calls = []

    def fake_ocr(image_png: bytes, page_no: int) -> PageText:
        calls.append(page_no)
        assert image_png.startswith(b"\x89PNG")
        return PageText(page_no=page_no, method="fake_ocr", text="OCR TEXT", words=[], ocr_confidence=0.9)

    run(db_session, storage, doc.id, ocr=fake_ocr)

    pages = pages_of(db_session, doc)
    assert calls == [2]
    assert (pages[0].method, pages[1].method) == ("text_layer", "fake_ocr")
    assert pages[1].ocr_confidence == pytest.approx(0.9)


def test_image_upload_is_ocrd(db_session):
    storage = MemoryStorage()
    png = pymupdf.open(stream=make_pdf([LAB_LINES]), filetype="pdf")[0].get_pixmap(dpi=72).tobytes("png")
    doc = add_document(db_session, storage, png, mime="image/png")

    run(db_session, storage, doc.id, ocr=lambda img, n: PageText(n, "fake_ocr", "OCR TEXT", [], 0.8))

    db_session.refresh(doc)
    assert doc.status == "done"
    assert [p.text for p in pages_of(db_session, doc)] == ["OCR TEXT"]


def test_image_without_ocr_engine_fails_with_code(db_session):
    storage = MemoryStorage()
    doc = add_document(db_session, storage, b"\x89PNG fake", mime="image/png")

    run(db_session, storage, doc.id, ocr=None)

    db_session.refresh(doc)
    assert (doc.status, doc.error_code) == ("failed", "ocr_unavailable")


def test_pdf_page_needing_ocr_without_engine_keeps_text_layer(db_session):
    storage = MemoryStorage()
    doc = add_document(db_session, storage, make_pdf([LAB_LINES, ["End of report"]]))

    run(db_session, storage, doc.id, ocr=None)

    db_session.refresh(doc)
    assert doc.status == "done"
    assert pages_of(db_session, doc)[1].text.strip() == "End of report"


def test_unexpected_error_marks_failed(db_session):
    storage = MemoryStorage()
    doc = add_document(db_session, storage, make_pdf([LAB_LINES]))
    storage.objects.clear()  # file missing from storage

    run(db_session, storage, doc.id)

    db_session.refresh(doc)
    assert (doc.status, doc.error_code) == ("failed", "processing_error")


def test_missing_document_is_ignored(db_session):
    import uuid

    run(db_session, MemoryStorage(), uuid.uuid4())  # deleted before the worker got to it: no crash


def test_ocr_boxes_on_pdf_pages_are_scaled_to_pdf_points(db_session):
    storage = MemoryStorage()
    doc = add_document(db_session, storage, make_pdf([["Scanned page"]]))
    box = {"text": "X", "x0": 200.0, "y0": 400.0, "x1": 600.0, "y1": 800.0, "conf": 0.9}

    run(db_session, storage, doc.id, ocr=lambda img, n: PageText(n, "fake_ocr", "X", [box], 0.9))

    [page] = pages_of(db_session, doc)
    # rendered at 200 dpi, PDF points are 1/72 inch
    assert page.words_json[0] == {"text": "X", "x0": 72.0, "y0": 144.0, "x1": 216.0, "y1": 288.0, "conf": 0.9}

