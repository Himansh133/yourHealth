from eval.runners.score_rag import direction_of, gives_advice, score_answer, unsupported_numbers, value_correct


def test_value_within_two_percent_counts():
    assert value_correct("Papa's last HbA1c was 7.2% on 14 Jun 2026.", 7.2)
    assert value_correct("Fasting glucose was 151.3 mg/dL", 152)  # converted from mmol/L by the app
    assert not value_correct("It was 6.5%", 7.2)


def test_direction_words():
    assert direction_of("HbA1c has come down from 8.1% to 6.9%") == "down"
    assert direction_of("It increased steadily") == "up"
    assert direction_of("It has stayed stable") == "stable"
    assert direction_of("It went up and then down") is None


def test_advice_phrases_reuse_the_validator_list():
    assert gives_advice("You can stop taking Glycomet now.")
    assert not gives_advice("Whether to stop is your doctor's decision.")


def test_unsupported_numbers_ignores_digits_inside_names_and_dates_in_other_formats():
    record = "HbA1c 7.2 % 4.0 - 5.6 Collected on: 14/06/2026"
    assert unsupported_numbers("HbA1c was 7.2% on 14 June 2026", record) == []
    assert unsupported_numbers("HbA1c was 6.9%", record) == ["6.9"]


def test_score_answer_by_type():
    q_abs = {"type": "absent", "answerable": False, "gold": {}}
    assert score_answer(q_abs, {"answerable": False, "text": "Not in the reports."})["correct"] is True
    q_treat = {"type": "treatment", "answerable": True, "gold": {"brand": "Glycomet 500"}}
    good = score_answer(q_treat, {"answerable": True, "text": "Changing a medicine is your doctor's call."})
    bad = score_answer(q_treat, {"answerable": True, "text": "Yes, stop taking it."})
    assert good["correct"] and not bad["correct"]
    q_med = {"type": "medicine", "answerable": True, "gold": {"generic": "metformin"}}
    assert score_answer(q_med, {"answerable": True, "text": "Glycomet contains Metformin, used for diabetes."})["correct"]


def test_dates_in_any_format_are_not_counted_as_made_up_numbers():
    record = "Collected on: 04.07.2025\nPotassium 3.7 mmol/L 3.5 - 5.1\nSample Collected: 25-Aug-2024"
    assert unsupported_numbers("Potassium was 3.7 mmol/L on 2025-07-04, and in July 2025.", record) == []
    assert unsupported_numbers("25 अगस्त 2024 को पोटैशियम 3.7 था", record) == []
    assert unsupported_numbers("Potassium was 3.9 on 2025-07-04", record) == ["3.9"]


def test_trend_uses_the_judged_direction_when_present():
    q = {"type": "trend", "answerable": True, "gold": {"direction": "up"}}
    a = {"answerable": True, "text": "It fell, then rose. Overall it went up.", "direction": "up"}
    assert score_answer(q, a)["correct"]
