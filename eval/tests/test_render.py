from datetime import date

import pymupdf
import pytest

from eval.generator.patients import Patient, Report
from eval.generator.render import LAYOUTS, render_report

PAPA = Patient(key="papa_01", display_name="Papa", sex="male", birth_year=1968, story="diabetic_metformin")
REPORT = Report(date(2026, 1, 10), {"4548-4": 8.1, "1558-6": 152.0, "2093-3": 182.0, "2085-9": 38.0, "2160-0": 1.02})


def text_of(pdf: bytes) -> str:
    with pymupdf.open(stream=pdf, filetype="pdf") as doc:
        return "\n".join(page.get_text() for page in doc)


@pytest.mark.parametrize("layout", list(LAYOUTS))
def test_every_layout_prints_each_truth_row(layout):
    pdf, truth = render_report(PAPA, REPORT, layout, doc_id="d1")
    text = text_of(pdf)
    assert truth["collected_on"] == "2026-01-10"
    assert {r["loinc"] for r in truth["rows"]} == set(REPORT.values)
    for row in truth["rows"]:
        assert row["printed_name"] in text and row["value"] in text


def test_si_layout_converts_units_and_keeps_the_canonical_value():
    _, truth = render_report(PAPA, REPORT, "si_units", doc_id="d1")
    glucose = next(r for r in truth["rows"] if r["loinc"] == "1558-6")
    assert glucose["unit"] == "mmol/L" and glucose["value"] == "8.4"
    assert glucose["canonical_value"] == 152.0


def test_flag_layout_prints_h_and_l():
    pdf, truth = render_report(PAPA, REPORT, "flags", doc_id="d1")
    hba1c = next(r for r in truth["rows"] if r["loinc"] == "4548-4")
    hdl = next(r for r in truth["rows"] if r["loinc"] == "2085-9")
    assert (hba1c["printed_flag"], hdl["printed_flag"]) == ("H", "L")


def test_one_sided_ranges_have_one_bound():
    _, truth = render_report(PAPA, REPORT, "classic", doc_id="d1")
    chol = next(r for r in truth["rows"] if r["loinc"] == "2093-3")
    assert (chol["range_low"], chol["range_high"]) == (None, "200")


def test_patient_name_and_lab_are_made_up_and_shown():
    pdf, truth = render_report(PAPA, REPORT, "classic", doc_id="d1")
    assert truth["lab_name"] in text_of(pdf)
    assert "Papa" in text_of(pdf)
