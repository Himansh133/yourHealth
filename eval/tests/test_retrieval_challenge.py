from app.services.chat.chunking import chunk_pages
from eval.runners.rechunk import window
from eval.runners.retrieval_challenge import corpus, reciprocal_rank


def test_challenge_has_long_similar_documents_and_intact_gold_at_every_size():
    docs, questions = corpus()
    assert len({q['id'] for q in questions}) == 6
    assert all(len(pages[0][1].split()) > 1000 for _, pages in docs)
    for size in (190, 300, 450):
        with window(size):
            chunks = [(name, c) for name, pages in docs for c in chunk_pages(pages, 'discharge')]
        assert all(len(c.text.split()) <= size for _, c in chunks)
        for q in questions:
            assert any(name == q['document'] and q['gold'] in c.text for name, c in chunks)
            assert not any(name != q['document'] and q['gold'] in c.text for name, c in chunks)


def test_retrieval_metric_counts_gold_rank_and_missing_candidates():
    assert reciprocal_rank([4, 2, 1], {1, 2}) == 0.5
    assert reciprocal_rank([4, 2, 1], {3}) == 0
