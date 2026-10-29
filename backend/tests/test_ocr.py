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
    assert set(first) == {"text", "x0", "y0", "x1", "y1", "conf", "ym"}
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


def test_tilt_is_estimated_from_box_top_edges():
    from app.services.extraction.ocr import estimate_tilt
    # two wide boxes whose top edge climbs 3 px over 100 px (about -1.7 degrees), one tiny box ignored
    boxes = [[[0, 10], [100, 7], [100, 27], [0, 30]], [[0, 50], [200, 44], [200, 64], [0, 70]],
             [[0, 0], [10, 9], [10, 19], [0, 10]]]
    assert round(estimate_tilt(boxes), 1) == -1.7


def test_rows_on_a_tilted_page_group_by_corrected_height():
    from app.services.extraction.ocr import group_rows
    # Tilted page: the value on the right sits 14 px higher than its name on the left, closer to the row above.
    words = [
        {"text": "HbA1c", "x0": 40, "y0": 100, "x1": 120, "y1": 112, "ym": 106},
        {"text": "8.1", "x0": 300, "y0": 86, "x1": 320, "y1": 98, "ym": 106},
        {"text": "Glucose", "x0": 40, "y0": 120, "x1": 120, "y1": 132, "ym": 126},
        {"text": "152", "x0": 300, "y0": 106, "x1": 320, "y1": 118, "ym": 126},
    ]
    assert [[w["text"] for w in row] for row in group_rows(words)] == [["HbA1c", "8.1"], ["Glucose", "152"]]
