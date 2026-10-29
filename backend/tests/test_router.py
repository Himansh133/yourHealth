from app.services.chat.router import route
from app.services.labs.dictionary import get_lab_dictionary

MEDS = {"glycomet", "metformin", "thyronorm", "levothyroxine"}


def r(question, meds=MEDS):
    return route(question, get_lab_dictionary(), meds)


def test_last_value_question_goes_to_sql_value():
    d = r("What was papa's last HbA1c?")
    assert d.labels == ["value"]
    assert [t.loinc_code for t in d.tests] == ["4548-4"]


def test_hinglish_value_question():
    assert r("papa ka hba1c kitna tha").labels == ["value"]


def test_trend_question_goes_to_sql_trend():
    d = r("Is mummy's vitamin D improving?")
    assert d.labels == ["trend"]
    assert d.tests[0].canonical_name.lower().startswith("vitamin d")


def test_hinglish_trend_word():
    assert r("sugar hba1c badha ya ghata?").labels == ["trend"]


def test_medicine_question():
    d = r("What is Thyronorm for?")
    assert d.labels == ["medicine"]
    assert d.medicines == ["thyronorm"]


def test_medicine_and_test_is_medicine_lab():
    d = r("Is Glycomet bringing my HbA1c down?")
    assert d.labels == ["medicine_lab"]
    assert [t.loinc_code for t in d.tests] == ["4548-4"]


def test_treatment_choice_wins_over_everything():
    assert r("Should I stop taking Glycomet since my HbA1c is better?").labels == ["treatment"]
    assert r("hba1c ke liye kaunsi dawai lu").labels == ["treatment"]


def test_test_alias_needs_whole_words():
    # "hb" is an alias, but not inside "hba1c"; "ldl" is an alias, but not inside "vldl"
    assert [t.loinc_code for t in r("latest hba1c").tests] == ["4548-4"]


def test_undecided_question_has_no_labels():
    d = r("What did the discharge summary say about diet?")
    assert d.labels == []


def test_general_question_about_a_test_is_left_undecided():
    d = r("What is HbA1c?")
    assert d.labels == []
    assert [t.loinc_code for t in d.tests] == ["4548-4"]


def test_everyday_words_cover_several_tests():
    d = r("How is papa's sugar now?")
    assert d.labels == ["value"]
    assert {t.loinc_code for t in d.tests} == {"4548-4", "1558-6"}


def test_thyroid_trend():
    d = r("Is mummy's thyroid getting better?")
    assert d.labels == ["trend"]
    assert {t.canonical_name for t in d.tests} == {"TSH", "Free T4"}


def test_exact_test_name_beats_everyday_word():
    assert [t.loinc_code for t in r("latest fasting blood sugar").tests] == ["1558-6"]


def test_treatment_question_about_sugar_keeps_the_tests():
    d = r("Which medicine should papa take for his sugar?")
    assert d.labels == ["treatment"]
    assert {t.loinc_code for t in d.tests} == {"4548-4", "1558-6"}


# --- LLM classifier (stage 2) -----------------------------------------------------------------------------------

import json

from app.services.chat.llm import FakeLLM, LLMError
from app.services.chat.router import classify


def test_classifier_returns_labels_and_test():
    llm = FakeLLM([json.dumps({"labels": ["trend"], "test": "creatinine"})])
    c = classify(llm, "How are papa's kidneys doing?")
    assert c.labels == ["trend"]
    assert c.test == "creatinine"
    assert "How are papa's kidneys doing?" in llm.prompts[0][1]


def test_classifier_drops_unknown_labels():
    c = classify(FakeLLM([json.dumps({"labels": ["poetry", "out_of_scope"], "test": None})]), "q")
    assert c.labels == ["out_of_scope"]


def test_classifier_failure_means_search_documents():
    class Down:
        def complete_json(self, system, user):
            raise LLMError("down")

    assert classify(Down(), "q").labels == ["document"]
    assert classify(FakeLLM(["not json"]), "q").labels == ["document"]
    assert classify(FakeLLM([json.dumps({"labels": []})]), "q").labels == ["document"]


def test_plural_everyday_word():
    d = r("How are papa's kidneys doing?")
    assert {t.canonical_name for t in d.tests} == {"Creatinine", "Uric acid"}


def test_classifier_prompt_separates_treatment_given_from_treatment_choice():
    from app.services.chat.router import CLASSIFIER_SYSTEM
    assert "treatment given" in CLASSIFIER_SYSTEM
    assert "follow-up" in CLASSIFIER_SYSTEM
