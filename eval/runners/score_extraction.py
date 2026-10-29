"""Compare extracted lab rows with the truth (plan 14.3). A row is correct only if test, value, unit and range all
match what was printed. Field counts show what breaks."""
from decimal import Decimal

from app.services.labs.normalize import NormalizedRow
from app.services.labs.values import normalize_unit


def _dec(s: str | None) -> Decimal | None:
    return None if s is None else Decimal(s)


def score_document(truth: dict, rows: list[NormalizedRow], doc_type: str, report_date: str | None) -> dict:
    by_loinc: dict[str, NormalizedRow] = {}
    for r in rows:
        if r.test and r.test.loinc_code not in by_loinc:
            by_loinc[r.test.loinc_code] = r

    fields = {"test": 0, "value": 0, "unit": 0, "range": 0}
    correct = 0
    for t in truth["rows"]:
        r = by_loinc.get(t["loinc"])
        if r is None:
            continue
        ok = {"test": True,
              "value": r.value_num == _dec(t["value"]),
              "unit": normalize_unit(r.raw.raw_unit) == normalize_unit(t["unit"]),
              "range": (r.range_low, r.range_high) == (_dec(t["range_low"]), _dec(t["range_high"]))}
        for k, v in ok.items():
            fields[k] += v
        correct += all(ok.values())
    return {"truth_rows": len(truth["rows"]), "extracted_rows": len(rows), "matched_rows": fields["test"],
            "correct_rows": correct, "fields": fields, "type_correct": doc_type == truth["kind"],
            "date_correct": report_date == truth["collected_on"]}


def summarize(docs: list[dict]) -> dict:
    truth = sum(d["truth_rows"] for d in docs)
    extracted = sum(d["extracted_rows"] for d in docs)
    correct = sum(d["correct_rows"] for d in docs)
    matched = sum(d["matched_rows"] for d in docs)
    p = correct / extracted if extracted else 0.0
    r = correct / truth if truth else 0.0
    return {
        "documents": len(docs), "truth_rows": truth, "precision": p, "recall": r,
        "f1": 2 * p * r / (p + r) if p + r else 0.0,
        # of the rows whose test was found, how often each other field was right
        "field_accuracy": {k: sum(d["fields"][k] for d in docs) / matched if matched else 0.0
                           for k in ("value", "unit", "range")},
        "test_found": matched / truth if truth else 0.0,
        "date_accuracy": sum(d["date_correct"] for d in docs) / len(docs) if docs else 0.0,
        "type_accuracy": sum(d["type_correct"] for d in docs) / len(docs) if docs else 0.0,
    }
