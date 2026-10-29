from app.services.chat.router import route
from app.services.labs.dictionary import get_lab_dictionary

MEDS = {"glycomet", "metformin", "thyronorm", "levothyroxine"}


def r(question, meds=MEDS):
    return route(question, get_lab_dictionary(), meds)


def test_last_value_question_goes_to_sql_value():
    d = r("What was papa's last HbA1c?")
    assert d.labels == ["value"]
    assert d.test.loinc_code == "4548-4"


def test_hinglish_value_question():
    assert r("papa ka hba1c kitna tha").labels == ["value"]


def test_trend_question_goes_to_sql_trend():
    d = r("Is mummy's vitamin D improving?")
    assert d.labels == ["trend"]
    assert d.test.canonical_name.lower().startswith("vitamin d")


def test_hinglish_trend_word():
    assert r("sugar hba1c badha ya ghata?").labels == ["trend"]


def test_medicine_question():
    d = r("What is Thyronorm for?")
    assert d.labels == ["medicine"]
    assert d.medicines == ["thyronorm"]


def test_medicine_and_test_is_medicine_lab():
    d = r("Is Glycomet bringing my HbA1c down?")
    assert d.labels == ["medicine_lab"]
    assert d.test.loinc_code == "4548-4"


def test_treatment_choice_wins_over_everything():
    assert r("Should I stop taking Glycomet since my HbA1c is better?").labels == ["treatment"]
    assert r("hba1c ke liye kaunsi dawai lu").labels == ["treatment"]


def test_test_alias_needs_whole_words():
    # "hb" is an alias, but not inside "hba1c"; "ldl" is an alias, but not inside "vldl"
    assert r("latest hba1c").test.loinc_code == "4548-4"


def test_undecided_question_has_no_labels():
    d = r("What did the discharge summary say about diet?")
    assert d.labels == []


def test_general_question_about_a_test_is_left_undecided():
    d = r("What is HbA1c?")
    assert d.labels == []
    assert d.test.loinc_code == "4548-4"
