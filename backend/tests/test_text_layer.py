import pymupdf

from app.services.extraction.text_layer import extract_text_layer, needs_ocr

LAB_LINES = [
    "Dr Demo Diagnostics            Sample Collected: 12/03/2026",
    "Test Name                Result     Unit       Reference Range",
    "HbA1c (Glycosylated Haemoglobin)    7.2    %    4.0 - 5.6",
    "TSH                     6.81     uIU/mL     0.35 - 5.50",
    "Haemoglobin             13.4     g/dL       13.0 - 17.0",
    "Vitamin D 25-OH         14.2     ng/mL      30 - 100",
]


def make_pdf(pages: list[list[str]]) -> bytes:
    doc = pymupdf.open()
    for lines in pages:
        page = doc.new_page()
        for i, line in enumerate(lines):
            page.insert_text((40, 60 + i * 18), line, fontsize=9)
    return doc.tobytes()


def make_image_only_pdf() -> bytes:
    """A 'scanned' page: the text is pixels, there is no text layer."""
    src = pymupdf.open(stream=make_pdf([LAB_LINES]), filetype="pdf")
    pix = src[0].get_pixmap(dpi=100)
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_image(page.rect, pixmap=pix)
    return doc.tobytes()


def test_extracts_text_per_page_with_page_numbers():
    pages = extract_text_layer(make_pdf([LAB_LINES, LAB_LINES[:3] + ["Page two marker"] * 10]))
    assert [p.page_no for p in pages] == [1, 2]
    assert "HbA1c" in pages[0].text
    assert "Page two marker" in pages[1].text


def test_text_keeps_line_order():
    [page] = extract_text_layer(make_pdf([LAB_LINES]))
    assert page.text.index("HbA1c") < page.text.index("TSH") < page.text.index("Vitamin D")


def test_words_have_boxes_for_highlighting():
    [page] = extract_text_layer(make_pdf([LAB_LINES]))
    hba1c = next(w for w in page.words if w["text"] == "HbA1c")
    assert set(hba1c) == {"text", "x0", "y0", "x1", "y1"}
    assert hba1c["x0"] < hba1c["x1"] and hba1c["y0"] < hba1c["y1"]


def test_method_is_text_layer_without_confidence():
    [page] = extract_text_layer(make_pdf([LAB_LINES]))
    assert page.method == "text_layer"
    assert page.ocr_confidence is None


def test_digital_lab_page_does_not_need_ocr():
    [page] = extract_text_layer(make_pdf([LAB_LINES]))
    assert needs_ocr(page) is False


def test_scanned_page_needs_ocr():
    [page] = extract_text_layer(make_image_only_pdf())
    assert page.text.strip() == ""
    assert needs_ocr(page) is True


def test_page_with_few_words_needs_ocr():
    [page] = extract_text_layer(make_pdf([["Scanned by CamScanner"]]))
    assert needs_ocr(page) is True


def test_garbage_text_needs_ocr():
    junk = ["ï¿½ï¿½ ~~ ## @@ §§ ^^ || ** %% ;; ::"] * 5
    [page] = extract_text_layer(make_pdf([junk]))
    assert needs_ocr(page) is True


def test_hindi_text_layer_is_not_garbage():
    from app.services.extraction.text_layer import PageText

    text = "हीमोग्लोबिन 13.4 g/dL सामान्य सीमा 13.0 - 17.0 " * 4
    words = [{"text": w, "x0": 0, "y0": 0, "x1": 1, "y1": 1} for w in text.split()]
    assert needs_ocr(PageText(page_no=1, method="text_layer", text=text, words=words)) is False
