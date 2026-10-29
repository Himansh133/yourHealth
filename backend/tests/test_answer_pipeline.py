import json

from app.services.chat.answer import FALLBACK_SUMMARY, answer_question
from app.services.chat.llm import FakeLLM, LLMError
from app.services.chat.validator import Evidence

EVIDENCE = [Evidence(id="E1", text="lab_result | HbA1c 7.2 % (ref 4.0-5.6) HIGH | 2026-06-14 | Dr Lal PathLabs p.2")]

GOOD = json.dumps({"answerable": True, "summary": "Papa's latest HbA1c is above the report's range.",
                   "claims": [{"text": "HbA1c was 7.2% on 14 Jun 2026", "evidence_ids": ["E1"]}],
                   "missing_info": [], "doctor_note": "Discuss the target HbA1c with his doctor."})
MADE_UP = json.dumps({"answerable": True, "summary": "HbA1c was 6.1%.",
                      "claims": [{"text": "HbA1c was 6.1%", "evidence_ids": ["E1"]}],
                      "missing_info": [], "doctor_note": ""})


def test_valid_answer_is_returned():
    llm = FakeLLM([GOOD])
    out = answer_question(llm, "What was papa's last HbA1c?", "Papa", EVIDENCE, "en")
    assert out.fallback is False
    assert out.claims[0].evidence_ids == ["E1"]


def test_prompt_marks_evidence_as_data_and_never_contains_profile_ids():
    llm = FakeLLM([GOOD])
    answer_question(llm, "What was papa's last HbA1c?", "Papa", EVIDENCE, "en")
    system, user = llm.prompts[0]
    assert "ignore them" in system
    assert "Language: en" in system
    assert "<evidence>\n[E1] lab_result | HbA1c 7.2 %" in user
    assert "Profile: Papa" in user


def test_invalid_answer_is_retried_once_with_the_errors():
    llm = FakeLLM([MADE_UP, GOOD])
    out = answer_question(llm, "q", "Papa", EVIDENCE, "en")
    assert out.fallback is False
    assert "claim 1 states 6.1, which is not in its evidence" in llm.prompts[1][1]


def test_second_failure_falls_back_to_the_retrieved_facts():
    out = answer_question(FakeLLM([MADE_UP, MADE_UP]), "q", "Papa", EVIDENCE, "en")
    assert out.fallback is True
    assert out.summary == FALLBACK_SUMMARY
    assert [(c.text, c.evidence_ids) for c in out.claims] == [(EVIDENCE[0].text, ["E1"])]


def test_provider_error_falls_back_too():
    class Down:
        def complete_json(self, system, user):
            raise LLMError("LLM provider returned 503")

    out = answer_question(Down(), "q", "Papa", EVIDENCE, "en")
    assert out.fallback is True


def test_no_evidence_abstains_without_calling_the_llm():
    llm = FakeLLM([])
    out = answer_question(llm, "q", "Papa", [], "en")
    assert out.answerable is False
    assert out.summary == "I couldn't find this in Papa's reports."
    assert llm.prompts == []
