from eval.runners.load_eval_db import EVAL_DB


def test_only_eval_databases_are_accepted():
    base = "postgresql+psycopg://yourhealth:yourhealth@localhost:5432/"
    assert EVAL_DB.search(base + "yourhealth_eval")
    assert EVAL_DB.search(base + "yourhealth_eval_v2")
    assert not EVAL_DB.search(base + "yourhealth")
    assert not EVAL_DB.search(base + "yourhealth_eval/../yourhealth")
