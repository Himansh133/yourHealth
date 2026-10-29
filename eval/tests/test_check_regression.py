from eval.runners.check_regression import check

BASE = {"f1": 0.981, "field_accuracy": {"value": 1.0}, "type_accuracy": 1.0, "date_accuracy": 1.0}


def run(**over):
    return check({**BASE, **over}, BASE)


def test_same_numbers_pass():
    assert run() == []


def test_small_f1_wobble_passes_but_a_two_point_drop_fails():
    assert run(f1=0.97) == []
    assert run(f1=0.95) == ["F1 dropped from 98.1% to 95.0% (allowed: 2 points)"]


def test_any_wrong_value_or_document_type_fails():
    assert run(field_accuracy={"value": 0.99}) == ["value accuracy is 99.0%; a wrong value must never pass"]
    assert run(type_accuracy=0.97) == ["document type accuracy is 97.0%; it was 100.0%"]
