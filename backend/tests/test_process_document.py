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



# --- lab results (plan 7.3, 8.4) -------------------------------------------------

from datetime import date  # noqa: E402
from decimal import Decimal  # noqa: E402

from app.db.models import LabResult, LabTestRecord  # noqa: E402

LAB_REPORT = [
    "Dr Lal PathLabs          Sample Collected: 12/03/2026 09:15",
    "Test Name                  Result    Unit      Reference Range",
    "HbA1c (Glycosylated Haemoglobin)   7.2   %   4.0 - 5.6",
    "TSH                        6.81      uIU/mL    0.35 - 5.50",
    "Fasting Blood Sugar        5.5       mmol/L    3.9 - 5.6",
    "Total Protein              7.1       g/dL      6.0 - 8.3",
]


def results_of(db, doc):
    return {r.raw_name: r for r in db.query(LabResult).filter_by(document_id=doc.id)}


def test_lab_report_rows_are_stored_normalised(db_session):
    storage = MemoryStorage()
    doc = add_document(db_session, storage, make_pdf([LAB_REPORT]))

    run(db_session, storage, doc.id)

    db_session.refresh(doc)
    assert (doc.doc_type, doc.report_date, doc.lab_name) == ("lab_report", date(2026, 3, 12), "Dr Lal PathLabs")
    assert doc.status == "done"
    rows = results_of(db_session, doc)
    assert set(rows) == {"HbA1c (Glycosylated Haemoglobin)", "TSH", "Fasting Blood Sugar", "Total Protein"}

    hba1c = rows["HbA1c (Glycosylated Haemoglobin)"]
    assert hba1c.profile_id == doc.profile_id
    assert db_session.get(LabTestRecord, hba1c.lab_test_id).loinc_code == "4548-4"
    assert (hba1c.raw_value, hba1c.raw_unit, hba1c.raw_range) == ("7.2", "%", "4.0 - 5.6")
    assert (hba1c.value_num, hba1c.flag, hba1c.observed_on) == (Decimal("7.2"), "high", date(2026, 3, 12))
    assert hba1c.page_no == 1 and hba1c.bbox["x0"] > 0
    assert hba1c.extraction_method == "regex"
    assert hba1c.verified_by_user is False

    sugar = rows["Fasting Blood Sugar"]
    assert round(sugar.value_canonical, 1) == Decimal("99.1")
    assert sugar.flag == "normal"

    assert rows["Total Protein"].lab_test_id is None  # unmapped but kept


def test_low_confidence_row_sends_document_to_review(db_session):
    storage = MemoryStorage()
    misread = LAB_REPORT[:2] + ["HbA1c   72   %   4.0 - 5.6", "TSH  6.81  uIU/mL  0.35 - 5.50",
                                "Creatinine  1.1  mg/dL  0.7 - 1.3"]
    doc = add_document(db_session, storage, make_pdf([misread]))

    run(db_session, storage, doc.id)

    db_session.refresh(doc)
    assert doc.status == "needs_review"


def test_missing_report_date_sends_to_review_and_uses_upload_date(db_session):
    storage = MemoryStorage()
    doc = add_document(db_session, storage, make_pdf([LAB_REPORT[1:]]))

    run(db_session, storage, doc.id)

    db_session.refresh(doc)
    assert doc.report_date is None
    assert doc.status == "needs_review"
    assert {r.observed_on for r in results_of(db_session, doc).values()} == {doc.created_at.date()}


def test_rerun_replaces_lab_results(db_session):
    storage = MemoryStorage()
    doc = add_document(db_session, storage, make_pdf([LAB_REPORT]))
    run(db_session, storage, doc.id)
    run(db_session, storage, doc.id)
    assert len(results_of(db_session, doc)) == 4


def test_non_lab_document_has_no_lab_results(db_session):
    storage = MemoryStorage()
    rx = ["Dr. A Sharma MBBS Reg. No 12345", "Rx", "Tab Glycomet 500 1-0-1 x 30 days", "Tab Telma 40 OD"] + \
         ["Advice: walk daily, avoid sugar, follow up after one month with reports"] * 3
    doc = add_document(db_session, storage, make_pdf([rx]))

    run(db_session, storage, doc.id)

    db_session.refresh(doc)
    assert (doc.doc_type, doc.status) == ("prescription", "done")
    assert results_of(db_session, doc) == {}


# --- prescriptions (plan 9.1) ----------------------------------------------------

from app.db.models import DrugBrand, ProfileMedicine  # noqa: E402
from app.refdata.load import load_reference_data  # noqa: E402

RX = [
    "Dr. A Sharma MBBS, MD   Reg. No 12345",
    "Rx",
    "1. Tab Glycomet GP 1  1-0-1 x 30 days",
    "2. Tab Telma 40  OD",
    "3. Tab Paracip 500  SOS",
    "Advice: walk daily, avoid sweets, review after one month with reports",
    "Follow up with HbA1c and lipid profile after three months please",
]


def meds_of(db, doc):
    return db.query(ProfileMedicine).filter_by(source_document_id=doc.id).order_by(ProfileMedicine.raw_text).all()


def test_prescription_creates_unconfirmed_medicines(db_session):
    load_reference_data(db_session)
    storage = MemoryStorage()
    doc = add_document(db_session, storage, make_pdf([RX]))

    run(db_session, storage, doc.id)

    db_session.refresh(doc)
    assert (doc.doc_type, doc.status) == ("prescription", "done")
    meds = meds_of(db_session, doc)
    assert [m.raw_text for m in meds] == ["1. Tab Glycomet GP 1 1-0-1 x 30 days", "2. Tab Telma 40 OD",
                                          "3. Tab Paracip 500 SOS"]
    assert all(m.confirmed_by_user is False and m.profile_id == doc.profile_id for m in meds)
    brands = [db_session.get(DrugBrand, m.brand_id).brand_name if m.brand_id else None for m in meds]
    assert brands == ["Glycomet GP 1", "Telma 40", None]  # unknown brand kept for the user to fix
    assert [m.frequency_code for m in meds] == ["BD", "OD", "SOS"]


def test_rerun_keeps_confirmed_and_replaces_unconfirmed(db_session):
    load_reference_data(db_session)
    storage = MemoryStorage()
    doc = add_document(db_session, storage, make_pdf([RX]))
    run(db_session, storage, doc.id)
    first = meds_of(db_session, doc)[0]
    first.confirmed_by_user = True
    db_session.commit()

    run(db_session, storage, doc.id)

    meds = meds_of(db_session, doc)
    assert len([m for m in meds if m.confirmed_by_user]) == 1
    assert len([m for m in meds if not m.confirmed_by_user]) == 2
