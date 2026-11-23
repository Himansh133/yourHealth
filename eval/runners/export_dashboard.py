"""Export aggregate-only historical benchmark data; never bundle patient answer logs."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PREFIX = "eval/results/2026-10-30-v2q2"


def build_dashboard(root: Path = ROOT) -> dict:
    report = f"{PREFIX}_rag_test.md"
    metrics = []
    for line in (root / report).read_text().splitlines():
        if not line.startswith("| "):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) != 4 or cells[0] == "Metric":
            continue
        metrics.append({"label": cells[0], "lower_is_better": "lower is better" in cells[0], "values": cells[1:]})
    sources = []
    counts = []
    for name in [report, *(f"{PREFIX}_rag_{system}_test.jsonl" for system in ("b0", "b1", "ours"))]:
        content = (root / name).read_bytes()
        sources.append({"path": name, "sha256": hashlib.sha256(content).hexdigest()})
        if name.endswith("jsonl"):
            counts.append(len(content.decode().splitlines()))
    if counts != [90, 90, 90] or not metrics:
        raise ValueError("Frozen benchmark files do not match the expected 90-question run")
    return {
        "run_date": "2026-10-30", "code_revision": "9321fce", "question_count": 90,
        "model": "DeepSeek-V4-Flash via GMI Cloud", "dataset": "Synthetic patients, v2 expanded test split",
        "systems": ["B0 · Plain LLM", "B1 · Vector RAG", "YourHealth pipeline"],
        "metrics": metrics, "sources": sources,
        "limitations": [
            "Historical results, not a measurement of the current build. Recent answer-format and retrieval changes need a new run.",
            "Synthetic data only; not clinical validation or a guarantee for real patient reports.",
            "The expanded test reused 57 previously evaluated questions; it is not a wholly untouched holdout.",
            "Small category samples: always read the denominator beside a percentage.",
            "Trend direction used an LLM judge. Number checks do not prove clinical correctness or complete semantic support.",
            "The medicine baselines had different reference-data access; that comparison does not isolate model quality.",
        ],
    }


if __name__ == "__main__":
    target = ROOT / "frontend/src/data/evaluation.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(build_dashboard(), indent=2, ensure_ascii=False) + "\n")
    print(f"Wrote aggregate benchmark: {target.relative_to(ROOT)}")
