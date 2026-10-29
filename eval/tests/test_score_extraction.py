from app.services.labs.dictionary import get_lab_dictionary
from app.services.labs.normalize import normalize_row
from app.services.labs.row_parser import RawRow

from eval.runners.score_extraction import score_document, summarize

TRUTH = {"collected_on": "2026-01-10", "kind": "lab_report", "rows": [
    {"loinc": "4548-4", "value": "8.1", "unit": "%", "range_low": "4.0", "range_high": "5.6"},
    {"loinc": "2093-3", "value": "182", "unit": "mg/dL", "range_low": None, "range_high": "200"},
]}


def row(name, value, unit, rng):
    return normalize_row(RawRow(name, value, unit, rng, None), get_lab_dictionary())


def test_all_rows_right():
    s = score_document(TRUTH, [row("HbA1c", "8.1", "%", "4.0 - 5.6"), row("Total Cholesterol", "182", "mg/dL", "< 200")],
                       "lab_report", "2026-01-10")
    assert (s["truth_rows"], s["extracted_rows"], s["correct_rows"]) == (2, 2, 2)
    assert s["date_correct"] and s["type_correct"]


def test_wrong_value_counts_against_the_value_field_only():
    s = score_document(TRUTH, [row("HbA1c", "8.7", "%", "4.0 - 5.6"), row("Total Cholesterol", "182", "mg/dL", "< 200")],
                       "lab_report", "2026-01-10")
    assert s["correct_rows"] == 1
    assert s["fields"] == {"test": 2, "value": 1, "unit": 2, "range": 2}


def test_unmapped_and_junk_rows_hurt_precision_not_recall_twice():
    rows = [row("HbA1c", "8.1", "%", "4.0 - 5.6"), row("Some Header", "12", None, None)]
    s = score_document(TRUTH, rows, "lab_report", None)
    assert (s["extracted_rows"], s["correct_rows"], s["date_correct"]) == (2, 1, False)


def test_summary_computes_precision_recall_f1():
    docs = [{"format": "pdf", "truth_rows": 10, "extracted_rows": 8, "correct_rows": 8, "date_correct": True,
             "type_correct": True, "fields": {"test": 8, "value": 8, "unit": 8, "range": 8}, "matched_rows": 8}]
    out = summarize(docs)
    assert out["precision"] == 1.0 and out["recall"] == 0.8 and round(out["f1"], 3) == 0.889
