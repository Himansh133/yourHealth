"""Run the backend's extraction on every generated document and score it against the truth (plan 14.5).

Usage (from backend/): PYTHONPATH=.. .venv/bin/python -m eval.runners.run_extraction [--split test]
Writes eval/results/<date>_extraction_<split>.md and .json.
"""
import argparse
import json
from collections import defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path

from app.services.extraction.classify import classify_document, find_report_date
from app.services.extraction.ocr import rapid_ocr
from app.services.labs.dictionary import get_lab_dictionary
from app.services.labs.normalize import normalize_row
from app.services.labs.row_parser import parse_words
from app.services.labs.values import normalize_unit
from app.workers.process_document import _extract_pages

from eval.runners.score_extraction import score_document, summarize

EVAL = Path(__file__).resolve().parents[1]


def extract(path: Path):
    mime = "application/pdf" if path.suffix == ".pdf" else "image/jpeg"
    pages = _extract_pages(path.read_bytes(), mime, rapid_ocr)
    d = get_lab_dictionary()
    rows = [normalize_row(r, d, p.ocr_confidence) for p in pages for r in parse_words(p.words)]
    text = "\n".join(p.text for p in pages)
    found = find_report_date(text)
    doc_type = classify_document(text, len(rows), sum(1 for r in rows if r.test))
    return rows, doc_type, found.isoformat() if found else None


def mistakes(truth: dict, rows) -> list[str]:
    by_loinc = {r.test.loinc_code: r for r in rows if r.test}
    out = []
    for t in truth["rows"]:
        r = by_loinc.get(t["loinc"])
        printed = f"{t['printed_name']} | {t['value']} {t['unit']} | {t['range_text']}"
        if r is None:
            near = [x.raw.raw_name for x in rows if x.test is None]
            out.append(f"{truth['doc_id']} ({truth['format']}, {truth['layout']}): not found: {printed}"
                       f"{'  [unmapped rows: ' + '; '.join(near[:3]) + ']' if near else ''}")
        elif (r.value_num, r.range_low, r.range_high) != (Decimal(t["value"]), *(None if x is None else Decimal(x) for x in (t["range_low"], t["range_high"]))) \
                or normalize_unit(r.raw.raw_unit) != normalize_unit(t["unit"]):
            out.append(f"{truth['doc_id']} ({truth['format']}, {truth['layout']}): {printed}  ->  read "
                       f"{r.raw.raw_value} {r.raw.raw_unit} | {r.raw.raw_range}")
    return out


def pct(x: float) -> str:
    return f"{100 * x:.1f}%"


def table(groups: dict[str, list[dict]]) -> list[str]:
    lines = ["| Group | Docs | Rows | Precision | Recall | F1 | Value | Unit | Range | Date | Type |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for name, docs in groups.items():
        s = summarize(docs)
        f = s["field_accuracy"]
        lines.append(f"| {name} | {s['documents']} | {s['truth_rows']} | {pct(s['precision'])} | {pct(s['recall'])} | "
                     f"{pct(s['f1'])} | {pct(f['value'])} | {pct(f['unit'])} | {pct(f['range'])} | "
                     f"{pct(s['date_accuracy'])} | {pct(s['type_accuracy'])} |")
    return lines


def main(split: str, data: Path) -> Path:
    docs, errors = [], []
    for truth_file in sorted((data / "truth").glob("*.json")):
        truth = json.loads(truth_file.read_text())
        if split != "all" and truth["split"] != split:
            continue
        rows, doc_type, found = extract(data / "docs" / truth["file"])
        docs.append(score_document(truth, rows, doc_type, found) | {"doc_id": truth["doc_id"],
                                                                     "format": truth["format"],
                                                                     "layout": truth["layout"]})
        errors += mistakes(truth, rows)

    by_format, by_layout = defaultdict(list), defaultdict(list)
    for d in docs:
        by_format[d["format"]].append(d)
        by_layout[d["layout"]].append(d)

    out_dir = EVAL / "results"
    out_dir.mkdir(exist_ok=True)
    stem = out_dir / f"{date.today().isoformat()}_extraction_{split}"
    md = [f"# Extraction results ({split} split, {data.name})", "",
          "A row is correct only if test, value, unit and range all match the printed report. Value, unit and range",
          "columns are accuracies over rows whose test was found.", "",
          *table({"**All**": docs}), "", "## By format", "", *table(dict(sorted(by_format.items()))), "",
          "## By layout", "", *table(dict(sorted(by_layout.items()))), "",
          f"## Mistakes ({len(errors)})", "", *[f"- {e}" for e in errors[:60]]]
    stem.with_suffix(".md").write_text("\n".join(md) + "\n")
    stem.with_suffix(".json").write_text(json.dumps({"summary": summarize(docs), "documents": docs}, indent=1))
    print("\n".join(md[:8 + 2]))
    return stem.with_suffix(".md")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=["dev", "test", "all"], default="dev")
    ap.add_argument("--data", type=Path, default=EVAL / "data" / "v1")
    args = ap.parse_args()
    print(main(args.split, args.data))
