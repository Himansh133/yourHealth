import json

from app.services.chat.llm import FakeLLM, LLMError
from app.services.chat.translate import numbers_match, translate_answer
from app.services.chat.validator import Answer, Claim

EN = Answer(answerable=True, summary="Papa's HbA1c is above the report's range.",
            claims=[Claim(text="HbA1c was 7.2% on 14 Jun 2026, above the range of 4.0-5.6", evidence_ids=["E1"])],
            missing_info=[], doctor_note="Discuss the target HbA1c with his doctor.")


def hindi(claim="14 जून 2026 को HbA1c 7.2% था, जो 4.0-5.6 की सीमा से ज़्यादा है", note="डॉक्टर से बात करें।"):
    return json.dumps({"summary": "पापा का HbA1c रिपोर्ट की सीमा से ज़्यादा है।", "claims": [claim],
                       "missing_info": [], "doctor_note": note}, ensure_ascii=False)


def test_translation_keeps_citations_and_numbers():
    out = translate_answer(FakeLLM([hindi()]), EN, glossary={"HbA1c": "पिछले 3 महीने की औसत शुगर"})
    assert out.claims[0].evidence_ids == ["E1"]
    assert "7.2%" in out.claims[0].text and out.summary.startswith("पापा")


def test_prompt_carries_the_glossary_and_keeps_test_names_in_english():
    llm = FakeLLM([hindi()])
    translate_answer(llm, EN, glossary={"HbA1c": "पिछले 3 महीने की औसत शुगर"})
    system, user = llm.prompts[0]
    assert "HbA1c = पिछले 3 महीने की औसत शुगर" in system and "digits 0-9" in system
    assert '"HbA1c was 7.2% on 14 Jun 2026' in user


def test_a_changed_number_is_retried_then_given_up():
    wrong = hindi(claim="HbA1c 7.5% था")
    assert translate_answer(FakeLLM([wrong, hindi()]), EN, glossary={}) is not None  # second try fixed it
    assert translate_answer(FakeLLM([wrong, wrong]), EN, glossary={}) is None


def test_devanagari_digits_are_rejected():
    deva = hindi(claim="१४ जून २०२६ को HbA1c ७.२% था, सीमा ४.०-५.६")
    assert translate_answer(FakeLLM([deva, deva]), EN, glossary={}) is None


def test_advice_added_in_hindi_is_rejected():
    advice = hindi(note="आप दवा बंद कर सकते हैं।")
    assert translate_answer(FakeLLM([advice, advice]), EN, glossary={}) is None


def test_wrong_shape_or_provider_error_gives_up():
    assert translate_answer(FakeLLM(["{}", "not json"]), EN, glossary={}) is None

    class Down:
        def complete_json(self, s, u):
            raise LLMError("down")

    assert translate_answer(Down(), EN, glossary={}) is None


def test_numbers_match_compares_as_multisets_and_ignores_digits_in_names():
    assert numbers_match("HbA1c 7.2 and 7.2", "HbA1c 7.2 और 7.2")
    assert not numbers_match("7.2 and 7.2", "7.2")


def test_a_number_inside_our_own_glossary_meaning_is_not_a_changed_number():
    # Found in the browser: every Hindi answer about HbA1c fell back to English because of the "3" in the gloss.
    glossed = hindi(claim="14 जून 2026 को HbA1c (पिछले 3 महीने की औसत शुगर) 7.2% था, जो 4.0-5.6 की सीमा से ज़्यादा है")
    out = translate_answer(FakeLLM([glossed]), EN, glossary={"HbA1c": "पिछले 3 महीने की औसत शुगर"})
    assert out is not None and "पिछले 3 महीने" in out.claims[0].text


def test_a_changed_number_next_to_the_glossary_meaning_is_still_caught():
    wrong = hindi(claim="14 जून 2026 को HbA1c (पिछले 3 महीने की औसत शुगर) 7.5% था, जो 4.0-5.6 की सीमा से ज़्यादा है")
    assert translate_answer(FakeLLM([wrong, wrong]), EN, glossary={"HbA1c": "पिछले 3 महीने की औसत शुगर"}) is None


def test_digits_in_a_glossary_test_name_are_not_a_changed_number():
    # From the eval: Hindi answers wrote out "Vitamin D, 25-OH total" and the 25 failed the check half the time.
    en = Answer(answerable=True, summary="Mummy's latest vitamin D was 34.5 ng/mL.", claims=[], missing_info=[],
                doctor_note="")
    named = json.dumps({"summary": "मम्मी का Vitamin D, 25-OH total (विटामिन D) 34.5 ng/mL था।", "claims": [],
                        "missing_info": [], "doctor_note": ""}, ensure_ascii=False)
    assert translate_answer(FakeLLM([named]), en, glossary={"Vitamin D, 25-OH total": "विटामिन D"}) is not None


def test_glossary_name_in_the_english_is_set_aside_too():
    en = Answer(answerable=True, summary="Vitamin D, 25-OH total was 34.5 ng/mL.", claims=[], missing_info=[],
                doctor_note="")
    hindi_ = json.dumps({"summary": "विटामिन D 34.5 ng/mL था।", "claims": [], "missing_info": [], "doctor_note": ""},
                        ensure_ascii=False)
    assert translate_answer(FakeLLM([hindi_]), en, glossary={"Vitamin D, 25-OH total": "विटामिन D"}) is not None
