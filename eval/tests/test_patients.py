from datetime import date

from eval.generator.patients import TESTS, generate_patients


def test_same_seed_gives_the_same_dataset():
    assert generate_patients(seed=1) == generate_patients(seed=1)
    assert generate_patients(seed=1) != generate_patients(seed=2)


def test_about_thirty_patients_with_several_reports_each():
    patients = generate_patients(seed=1)
    assert 25 <= len(patients) <= 35
    assert all(3 <= len(p.reports) <= 6 for p in patients)
    assert len({p.key for p in patients}) == len(patients)


def test_reports_are_in_date_order_and_after_2023():
    for p in generate_patients(seed=1):
        dates = [r.collected_on for r in p.reports]
        assert dates == sorted(dates) and dates[0] >= date(2024, 1, 1)


def test_diabetic_story_hba1c_falls_after_metformin_and_b12_drifts_down():
    p = next(p for p in generate_patients(seed=1) if p.story == "diabetic_metformin")
    [med] = [m for m in p.medicines if m.brand == "Glycomet 500"]
    hba1c = [(r.collected_on, r.values["4548-4"]) for r in p.reports if "4548-4" in r.values]
    before = [v for d, v in hba1c if d < med.started_on]
    after = [v for d, v in hba1c if d > med.started_on]
    assert before and after and max(after) < min(before)
    b12 = [r.values["2132-9"] for r in p.reports if "2132-9" in r.values]
    assert b12[-1] < b12[0]


def test_healthy_patients_have_values_inside_the_range():
    healthy = [p for p in generate_patients(seed=1) if p.story == "healthy"]
    assert healthy
    for p in healthy:
        for r in p.reports:
            for loinc, v in r.values.items():
                low, high = TESTS[loinc].range_for(p.sex)
                assert (low is None or v >= low) and (high is None or v <= high), (loinc, v)


def test_every_medicine_is_a_known_brand():
    import csv
    from pathlib import Path
    seed = Path(__file__).resolve().parents[2] / "refdata" / "seed" / "drug_brands.csv"
    brands = {r["brand_name"] for r in csv.DictReader(seed.open())}
    assert {m.brand for p in generate_patients(seed=1) for m in p.medicines} <= brands
