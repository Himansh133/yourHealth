from app.services.chat.doc_search import rrf


def test_rrf_rewards_items_ranked_well_in_both_lists():
    assert rrf([["a", "b", "c"], ["c", "a", "d"]]) == ["a", "c", "b", "d"]


def test_rrf_with_one_list_keeps_its_order():
    assert rrf([["x", "y"]]) == ["x", "y"]


def test_rrf_with_empty_lists():
    assert rrf([[], []]) == []
