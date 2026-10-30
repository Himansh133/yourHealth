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


def test_note_about_the_evidence_goes_before_it():
    llm = FakeLLM([GOOD])
    answer_question(llm, "papa ka pichhla hba1c?", "Papa", EVIDENCE, "hi", note="These are the most recent values.",
                    hindi_mode="direct")
    assert "Note: These are the most recent values.\n<evidence>" in llm.prompts[0][1]


HINDI = json.dumps({"summary": "पापा का हाल का HbA1c रिपोर्ट की सीमा से ज़्यादा है।",
                    "claims": ["14 Jun 2026 को HbA1c 7.2% था"], "missing_info": [],
                    "doctor_note": "डॉक्टर से HbA1c के लक्ष्य पर बात करें।"}, ensure_ascii=False)


def test_hindi_is_written_in_english_validated_then_translated():
    llm = FakeLLM([GOOD, HINDI])
    out = answer_question(llm, "papa ka hba1c?", "Papa", EVIDENCE, "hi", hindi_mode="translate",
                          glossary={"HbA1c": "पिछले 3 महीने की औसत शुगर"})
    assert "Language: en" in llm.prompts[0][0]
    assert (out.lang, out.summary) == ("hi", "पापा का हाल का HbA1c रिपोर्ट की सीमा से ज़्यादा है।")
    assert out.claims[0].evidence_ids == ["E1"]


def test_failed_translation_falls_back_to_the_checked_english():
    wrong = HINDI.replace("7.2%", "7.5%")
    out = answer_question(FakeLLM([GOOD, wrong, wrong]), "q", "Papa", EVIDENCE, "hi", hindi_mode="translate")
    assert out.lang == "en" and out.summary == "Papa's latest HbA1c is above the report's range."


def test_direct_mode_writes_hindi_in_one_call():
    llm = FakeLLM([GOOD])
    out = answer_question(llm, "q", "Papa", EVIDENCE, "hi", hindi_mode="direct")
    assert "Language: hi" in llm.prompts[0][0] and len(llm.prompts) == 1 and out.lang == "hi"


def test_not_found_message_in_hindi():
    out = answer_question(FakeLLM([]), "q", "Papa", [], "hi")
    assert out.summary == "Papa की रिपोर्ट में यह नहीं मिला।" and out.lang == "hi"


def test_without_the_validator_the_first_answer_is_shown_as_written():
    llm = FakeLLM([MADE_UP])
    out = answer_question(llm, "q", "Papa", EVIDENCE, "en", validate=False)
    assert out.fallback is False
    assert out.summary == "HbA1c was 6.1%."
    assert len(llm.prompts) == 1


def test_without_the_validator_a_reply_that_is_not_json_still_falls_back():
    out = answer_question(FakeLLM(["not json", "not json"]), "q", "Papa", EVIDENCE, "en", validate=False)
    assert out.fallback is True
