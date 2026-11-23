"""Generate three clearly synthetic PDFs for the presentation; no database writes."""
from pathlib import Path

import pymupdf

REPORTS = [
    ("2026-01-10", "10 Jan 2026", "8.1", "152", "1.0"),
    ("2026-03-12", "12 Mar 2026", "7.6", "135", "1.1"),
    ("2026-06-14", "14 Jun 2026", "7.2", "119", "1.0"),
]


def generate_demo(destination: Path) -> list[Path]:
    destination.mkdir(parents=True, exist_ok=True)
    paths = []
    for iso, label, hba1c, glucose, creatinine in REPORTS:
        path = destination / f"sample-{iso}.pdf"
        lines = [
            "DEMONSTRATION LABORATORY", "SYNTHETIC DEMO DATA - NOT A REAL PATIENT", "",
            "Patient: Sample Patient", f"Report Date: {label}", "LABORATORY REPORT", "",
            "Test                  Result    Unit     Reference Range", "",
            f"HbA1c                 {hba1c}       %        4.0-5.6",
            f"Fasting Glucose       {glucose}       mg/dL    70-100",
            f"Creatinine            {creatinine}       mg/dL    0.7-1.3", "",
            "Values are fictional and intended for software demonstrations.",
            "No diagnosis, prescription or clinical validation is implied.",
        ]
        with pymupdf.open() as doc:
            page = doc.new_page()
            page.insert_text((40, 60), "\n".join(lines), fontname="cour", fontsize=10, lineheight=1.7)
            doc.set_metadata({"title": f"Synthetic demo report - {iso}", "subject": "Fictional demonstration data"})
            doc.save(path, garbage=4, deflate=True, no_new_id=True)
        paths.append(path)
    return paths


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    for path in generate_demo(root / "frontend/public/demo"):
        print(path.relative_to(root))
