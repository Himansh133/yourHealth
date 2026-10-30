"""Build the synthetic evaluation dataset (plan 14.2). Deterministic for a given seed.

Usage (from backend/): PYTHONPATH=.. .venv/bin/python -m eval.generator.build [--seed 1] [--out ../eval/data/v1]
"""
import argparse
import json
import random
from dataclasses import asdict
from datetime import timedelta
from pathlib import Path

from eval.generator.degrade import to_photo
from eval.generator.patients import generate_patients
from eval.generator.questions import injection_questions, make_questions, more_questions
from eval.generator.render import LAYOUTS, STORY_DIAGNOSES, render_discharge, render_report

FORMATS = [("pdf", 0.6), ("photo_clean", 0.2), ("photo_degraded", 0.2)]
TEST_SHARE = 0.3


def build(out: Path, seed: int = 1) -> dict:
    rng = random.Random(seed)
    patients = generate_patients(seed)
    (out / "docs").mkdir(parents=True, exist_ok=True)
    (out / "truth").mkdir(parents=True, exist_ok=True)

    keys = [p.key for p in patients]
    rng.shuffle(keys)
    test_keys = set(keys[:round(len(keys) * TEST_SHARE)])

    counts = {f: 0 for f, _ in FORMATS}
    latest_lab: dict[str, tuple] = {}  # patient -> (date, lab name) of their last report
    for p in patients:
        for i, report in enumerate(p.reports, 1):
            doc_id = f"{p.key}_r{i:02d}"
            layout = rng.choice(list(LAYOUTS))
            fmt = rng.choices([f for f, _ in FORMATS], weights=[w for _, w in FORMATS])[0]
            pdf, truth = render_report(p, report, layout, doc_id)
            latest_lab[p.key] = (report.collected_on, truth["lab_name"])
            if fmt == "pdf":
                name, data = f"{doc_id}.pdf", pdf
            else:
                name, data = f"{doc_id}.jpg", to_photo(pdf, rng, degraded=fmt == "photo_degraded")
            (out / "docs" / name).write_bytes(data)
            truth |= {"file": name, "format": fmt, "split": "test" if p.key in test_keys else "dev"}
            (out / "truth" / f"{doc_id}.json").write_text(json.dumps(truth, indent=1, ensure_ascii=False))
            counts[fmt] += 1

    (out / "patients.json").write_text(json.dumps(
        [asdict(p) | {"split": "test" if p.key in test_keys else "dev"} for p in patients],
        indent=1, default=str, ensure_ascii=False))
    # Discharge summaries with a planted instruction (plan 14.2 prompt-injection set), for every other patient within
    # each split, so both splits have some. Their own random generator: earlier documents stay exactly as they were.
    note_rng = random.Random(seed + 1000)
    with_note, discharges = set(), {}
    for split_keys in (sorted(test_keys), sorted(set(keys) - test_keys)):
        with_note |= set(split_keys[::2])
    for p in patients:
        if p.key not in with_note:
            continue
        on = p.reports[-1].collected_on + timedelta(days=note_rng.randint(5, 30))
        discharges[p.key] = on
        pdf, truth = render_discharge(p, on, STORY_DIAGNOSES[p.story][0], f"{p.key}_d01")
        (out / "docs" / f"{p.key}_d01.pdf").write_bytes(pdf)
        truth |= {"file": f"{p.key}_d01.pdf", "format": "pdf", "split": "test" if p.key in test_keys else "dev"}
        (out / "truth" / f"{p.key}_d01.json").write_text(json.dumps(truth, indent=1, ensure_ascii=False))
        counts["pdf"] += 1

    questions = (make_questions(patients, test_keys) + injection_questions(patients, with_note, test_keys)
                 + more_questions(patients, discharges, latest_lab, test_keys))
    for split in ("dev", "test"):
        with (out / f"questions_{split}.jsonl").open("w") as f:
            for q in questions:
                if q["split"] == split:
                    f.write(json.dumps(q, ensure_ascii=False) + "\n")
    return {"patients": len(patients), "documents": sum(counts.values()), **counts,
            "rows": sum(len(r.values) for p in patients for r in p.reports), "questions": len(questions)}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--out", type=Path, default=Path(__file__).resolve().parents[1] / "data" / "v1")
    args = ap.parse_args()
    print(build(args.out, args.seed))
