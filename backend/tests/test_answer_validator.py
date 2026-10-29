import json

from app.services.chat.validator import Evidence, validate_answer

EVIDENCE = [
    Evidence(id="E1", text="lab_result | HbA1c 7.2 % (ref 4.0-5.6) HIGH | 2026-06-14 | Dr Lal PathLabs p.2"),
    Evidence(id="E2", text="lab_result | HbA1c 8.1 % (ref 4.0-5.6) HIGH | 2026-01-10 | Thyrocare p.1"),
]


def answer(summary="Papa's HbA1c came down.", claims=None, **extra):
    body = {"answerable": True, "summary": summary,
            "claims": claims if claims is not None else [{"text": "HbA1c was 7.2% on 14 Jun 2026", "evidence_ids": ["E1"]}],
            "missing_info": [], "doctor_note": "Discuss the target with his doctor."}
    body.update(extra)
    return json.dumps(body)


def test_grounded_answer_passes():
    parsed, errors = validate_answer(answer(), EVIDENCE)
    assert errors == []
    assert parsed.claims[0].evidence_ids == ["E1"]


def test_invalid_json_fails():
    parsed, errors = validate_answer("not json", EVIDENCE)
    assert parsed is None
    assert errors and "schema" in errors[0]


def test_missing_field_fails_schema():
    parsed, errors = validate_answer(json.dumps({"answerable": True}), EVIDENCE)
    assert parsed is None
    assert errors


def test_unknown_evidence_id_fails():
    _, errors = validate_answer(answer(claims=[{"text": "HbA1c was high", "evidence_ids": ["E9"]}]), EVIDENCE)
    assert errors == ["claim 1 cites unknown evidence E9"]


def test_claim_without_citation_fails():
    _, errors = validate_answer(answer(claims=[{"text": "HbA1c was high", "evidence_ids": []}]), EVIDENCE)
    assert errors == ["claim 1 cites no evidence"]


def test_number_not_in_cited_evidence_fails():
    # 8.1 exists, but only in E2, which this claim doesn't cite
    _, errors = validate_answer(answer(claims=[{"text": "HbA1c was 8.1%", "evidence_ids": ["E1"]}]), EVIDENCE)
    assert errors == ["claim 1 states 8.1, which is not in its evidence"]


def test_computed_number_fails():
    _, errors = validate_answer(answer(claims=[{"text": "HbA1c dropped by 0.9", "evidence_ids": ["E1", "E2"]}]), EVIDENCE)
    assert errors == ["claim 1 states 0.9, which is not in its evidence"]


def test_dates_in_other_formats_and_trailing_zeros_pass():
    claims = [{"text": "On 10/01/2026 HbA1c was 8.10%", "evidence_ids": ["E2"]}]
    _, errors = validate_answer(answer(claims=claims), EVIDENCE)
    assert errors == []


def test_summary_numbers_must_be_somewhere_in_evidence():
    _, errors = validate_answer(answer(summary="HbA1c fell from 8.1% to 6.5%."), EVIDENCE)
    assert errors == ["summary states 6.5, which is not in the evidence"]


def test_advice_phrase_fails():
    _, errors = validate_answer(answer(doctor_note="You can stop taking metformin."), EVIDENCE)
    assert errors == ["doctor_note gives medical advice ('stop taking')"]


def test_hinglish_advice_phrase_fails():
    _, errors = validate_answer(answer(summary="Ab dawai band kar sakte hain."), EVIDENCE)
    assert errors == ["summary gives medical advice ('dawai band')"]


def test_diagnosis_phrase_fails():
    _, errors = validate_answer(answer(summary="You have diabetes."), EVIDENCE)
    assert errors == ["summary gives medical advice ('you have diabetes')"]


def test_unanswerable_answer_with_no_claims_passes():
    raw = json.dumps({"answerable": False, "summary": "Your reports don't mention this.", "claims": [],
                      "missing_info": ["No lipid profile uploaded"], "doctor_note": ""})
    parsed, errors = validate_answer(raw, EVIDENCE)
    assert errors == []
    assert parsed.answerable is False


def test_digits_inside_test_names_are_not_numbers():
    evidence = [Evidence(id="E1", text="drug_effect | metformin and Vitamin B12: lowers it (worth checking)")]
    claims = [{"text": "Metformin can lower vitamin B12, and is used to bring HbA1c and T4 levels into range",
               "evidence_ids": ["E1"]}]
    _, errors = validate_answer(answer(summary="It affects HbA1c.", claims=claims), evidence)
    assert errors == []


def test_numbers_with_units_attached_are_still_checked():
    _, errors = validate_answer(answer(claims=[{"text": "Dose is 850mg", "evidence_ids": ["E1"]}]), EVIDENCE)
    assert errors == ["claim 1 states 850, which is not in its evidence"]
