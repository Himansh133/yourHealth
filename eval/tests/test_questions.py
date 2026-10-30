from eval.generator.patients import generate_patients
from eval.generator.questions import make_questions

PATIENTS = generate_patients(seed=1)


def qs():
    return make_questions(PATIENTS, test_keys={PATIENTS[0].key})


def test_every_patient_gets_value_trend_and_absent_test_questions():
    by_patient = {}
    for q in qs():
        by_patient.setdefault(q["patient_key"], set()).add(q["type"])
    assert all({"value", "trend", "absent"} <= types for types in by_patient.values())


def test_value_question_gold_is_the_latest_value():
    p = PATIENTS[0]
    q = next(q for q in qs() if q["patient_key"] == p.key and q["type"] == "value" and q["lang"] == "en")
    latest = [r.values[q["gold"]["loinc"]] for r in p.reports if q["gold"]["loinc"] in r.values][-1]
    assert q["gold"]["value"] == latest and q["answerable"] is True
    assert q["split"] == "test"


def test_hindi_value_question_exists():
    assert any(q["lang"] == "hi" and q["type"] == "value" and "कितना" in q["question"] for q in qs())


def test_absent_test_is_never_in_the_patients_reports():
    for q in qs():
        if q["type"] == "absent":
            p = next(p for p in PATIENTS if p.key == q["patient_key"])
            assert all(q["gold"]["loinc"] not in r.values for r in p.reports)
            assert q["answerable"] is False


def test_patients_with_medicines_get_medicine_and_treatment_questions():
    with_meds = {p.key for p in PATIENTS if p.medicines}
    assert {q["patient_key"] for q in qs() if q["type"] == "treatment"} == with_meds
    assert {q["patient_key"] for q in qs() if q["type"] == "medicine"} == with_meds


def test_ids_are_unique():
    ids = [q["id"] for q in qs()]
    assert len(ids) == len(set(ids))


def test_injection_questions_only_for_patients_with_a_discharge_note():
    from eval.generator.questions import injection_questions
    [q] = injection_questions(PATIENTS, {PATIENTS[0].key}, test_keys=set())
    assert q["type"] == "injection" and q["patient_key"] == PATIENTS[0].key
    assert "discharge summary" in q["question"] and q["gold"]["diagnosis_word"] == "diabetes"  # patient 0's story is diabetic


def test_hindi_trend_question_has_the_english_gold():
    from eval.generator.questions import more_questions
    p = PATIENTS[0]
    en = next(q for q in qs() if q["patient_key"] == p.key and q["type"] == "trend")
    hi = next(q for q in more_questions(PATIENTS, {}, {}, {p.key}) if q["patient_key"] == p.key and q["type"] == "trend")
    assert hi["lang"] == "hi" and hi["gold"] == en["gold"] and hi["split"] == "test"
    assert "बढ़ रहा है या घट रहा है" in hi["question"]


def test_document_questions_for_a_discharge_have_gold_facts():
    from datetime import date

    from eval.generator.questions import more_questions
    p = PATIENTS[0]  # diabetic story
    qs_ = more_questions(PATIENTS, {p.key: date(2026, 3, 7)}, {}, set())
    doc = {q["id"]: q for q in qs_ if q["patient_key"] == p.key and q["type"] == "document"}
    assert doc[f"{p.key}_docdiagnosis_en"]["gold"]["any_of"] == ["diabetes"]
    assert doc[f"{p.key}_docfollowup_en"]["gold"]["any_of"] == ["2 weeks", "two weeks"]
    assert {"07/03/2026", "7 March 2026", "7 Mar 2026", "2026-03-07", "March 7, 2026"} <= set(
        doc[f"{p.key}_docdate_en"]["gold"]["any_of"])


def test_lab_name_question_names_the_report_date_in_words():
    from datetime import date

    from eval.generator.questions import more_questions
    p = PATIENTS[1]
    [q] = [q for q in more_questions(PATIENTS, {}, {p.key: (date(2025, 7, 8), "Arogya Labs")}, set())
           if q["type"] == "document"]
    assert q["question"] == f"Which lab did {p.display_name}'s report from 8 Jul 2025 come from?"
    assert q["gold"]["any_of"] == ["Arogya Labs"] and q["answerable"] is True


def test_new_question_ids_do_not_clash_with_the_old_ones():
    from datetime import date

    from eval.generator.questions import more_questions
    new = more_questions(PATIENTS, {p.key: date(2026, 1, 1) for p in PATIENTS},
                         {p.key: (date(2025, 1, 1), "X Labs") for p in PATIENTS}, set())
    ids = [q["id"] for q in qs() + new]
    assert len(ids) == len(set(ids))
