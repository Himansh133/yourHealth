"""Medium test: runs the real RapidOCR models (~2 s)."""
import pymupdf

from app.services.extraction.ocr import rapid_ocr

LINES = [
    "HbA1c (Glycosylated Haemoglobin)    7.2    %    4.0 - 5.6",
    "Haemoglobin             13.4     g/dL       13.0 - 17.0",
]


def render_png(lines, dpi=200) -> bytes:
    doc = pymupdf.open()
    page = doc.new_page()
    for i, line in enumerate(lines):
        page.insert_text((40, 60 + i * 18), line, fontsize=9)
    return page.get_pixmap(dpi=dpi).tobytes("png")


def test_reads_lines_top_to_bottom():
    page = rapid_ocr(render_png(LINES), page_no=3)
    assert page.page_no == 3
    assert page.method == "rapidocr"
    lines = page.text.splitlines()
    assert "HbA1c" in lines[0] and "7.2" in lines[0]
    assert "Haemoglobin" in lines[1] and "13.4" in lines[1]


def test_boxes_and_confidence():
    page = rapid_ocr(render_png(LINES), page_no=1)
    assert 0.8 < page.ocr_confidence <= 1.0
    first = page.words[0]
    assert set(first) == {"text", "x0", "y0", "x1", "y1", "conf"}
    assert first["y1"] < page.words[1]["y0"]  # first line is above the second


def test_blank_image_gives_empty_page():
    doc = pymupdf.open()
    png = doc.new_page().get_pixmap(dpi=72).tobytes("png")
    page = rapid_ocr(png, page_no=1)
    assert page.text == ""
    assert page.ocr_confidence is None


def test_group_rows_joins_boxes_on_same_line():
    from app.services.extraction.ocr import group_rows

    name = {"text": "Haemoglobin", "x0": 10, "y0": 100, "x1": 120, "y1": 120}
    value = {"text": "13.4 g/dL", "x0": 300, "y0": 101, "x1": 380, "y1": 121}
    next_row = {"text": "TSH", "x0": 10, "y0": 130, "x1": 50, "y1": 150}
    rows = group_rows([value, next_row, name])
    assert [[b["text"] for b in r] for r in rows] == [["Haemoglobin", "13.4 g/dL"], ["TSH"]]
