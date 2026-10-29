import io
import random
from datetime import date

from PIL import Image

from eval.generator.degrade import to_photo
from eval.generator.patients import Patient, Report
from eval.generator.render import render_report

PAPA = Patient(key="papa_01", display_name="Papa", sex="male", birth_year=1968, story="healthy")
PDF, _ = render_report(PAPA, Report(date(2026, 1, 10), {"4548-4": 5.2}), "classic", "d1")


def test_clean_photo_is_an_upright_jpeg():
    img = Image.open(io.BytesIO(to_photo(PDF, random.Random(1), degraded=False)))
    assert img.format == "JPEG" and img.height > img.width


def test_degraded_photo_is_deterministic_and_different_from_clean():
    a = to_photo(PDF, random.Random(1), degraded=True)
    assert a == to_photo(PDF, random.Random(1), degraded=True)
    assert a != to_photo(PDF, random.Random(1), degraded=False)


def test_build_writes_documents_truth_and_patients(tmp_path):
    import json

    from eval.generator.build import build
    summary = build(tmp_path, seed=1)
    assert summary["documents"] == len(list((tmp_path / "docs").iterdir())) == len(list((tmp_path / "truth").iterdir()))
    truth = json.loads(next((tmp_path / "truth").iterdir()).read_text())
    assert (tmp_path / "docs" / truth["file"]).exists() and truth["split"] in ("dev", "test")
    patients = json.loads((tmp_path / "patients.json").read_text())
    assert {p["split"] for p in patients} == {"dev", "test"}


def test_shadow_has_no_hard_black_bands():
    from eval.generator.degrade import _shadow
    white = Image.new("RGB", (300, 600), (255, 255, 255))
    shaded = _shadow(white, 0.6).convert("L")
    top, middle, bottom = (shaded.getpixel((150, y)) for y in (5, 300, 595))
    assert top == middle == bottom  # the shade changes across the page, not down it
    assert shaded.getpixel((5, 300)) != shaded.getpixel((295, 300))
