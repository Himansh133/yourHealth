from pathlib import Path

import pymupdf as fitz

from eval.runners.presentation_demo import generate_demo


def test_three_reports_are_dated_synthetic_and_parseable(tmp_path):
    from app.services.labs.row_parser import parse_line
    paths = generate_demo(tmp_path)
    assert len(paths) == 3
    for path in paths:
        with fitz.open(path) as doc:
            text = "".join(p.get_text() for p in doc)
        assert "SYNTHETIC DEMO DATA" in text
        assert "NOT A REAL PATIENT" in text
        assert "HbA1c" in text and "Creatinine" in text
        assert len([r for line in text.splitlines() if (r := parse_line(line))]) >= 3
    assert {p.name for p in paths} == {"sample-2026-01-10.pdf", "sample-2026-03-12.pdf", "sample-2026-06-14.pdf"}
