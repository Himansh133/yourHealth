"""CI gate for extraction (plan 14.6): fail if F1 drops more than 2 points from the committed baseline, if any
extracted value is wrong, or if document type or date accuracy falls.

Usage (from backend/): PYTHONPATH=.. .venv/bin/python -m eval.runners.check_regression <extraction .json>
"""
import json
import sys
from pathlib import Path

BASELINE = Path(__file__).resolve().parents[1] / "results" / "baseline_extraction_test.json"
F1_DROP_ALLOWED = 0.02


def check(now: dict, base: dict) -> list[str]:
    problems = []
    if now["f1"] < base["f1"] - F1_DROP_ALLOWED:
        problems.append(f"F1 dropped from {base['f1']:.1%} to {now['f1']:.1%} (allowed: 2 points)")
    if now["field_accuracy"]["value"] < 1.0:
        problems.append(f"value accuracy is {now['field_accuracy']['value']:.1%}; a wrong value must never pass")
    for key, label in (("type_accuracy", "document type"), ("date_accuracy", "report date")):
        if now[key] < base[key]:
            problems.append(f"{label} accuracy is {now[key]:.1%}; it was {base[key]:.1%}")
    return problems


if __name__ == "__main__":
    now = json.loads(Path(sys.argv[1]).read_text())["summary"]
    problems = check(now, json.loads(BASELINE.read_text()))
    print("\n".join(problems) or f"extraction OK: F1 {now['f1']:.1%}, value accuracy {now['field_accuracy']['value']:.0%}")
    sys.exit(1 if problems else 0)
