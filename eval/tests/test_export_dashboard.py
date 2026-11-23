import json
from pathlib import Path

from eval.runners.export_dashboard import build_dashboard

ROOT = Path(__file__).resolve().parents[2]


def test_dashboard_preserves_frozen_counts_and_contains_no_patient_answers():
    data = build_dashboard(ROOT)
    assert data["question_count"] == 90
    assert data["run_date"] == "2026-10-30"
    assert data["code_revision"] == "9321fce"
    numeric = next(m for m in data["metrics"] if m["label"].startswith("Numeric accuracy, value questions (English)"))
    assert numeric["values"][2] == "100% (9/9)"
    assert len(data["sources"]) == 4
    assert all(len(s["sha256"]) == 64 for s in data["sources"])
    encoded = json.dumps(data)
    assert '"text"' not in encoded and "papa_01" not in encoded
    assert data == json.loads((ROOT / "frontend/src/data/evaluation.json").read_text())
