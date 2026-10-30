from app.services.chat import chunking
from eval.runners.rechunk import window


def test_window_sets_the_chunk_size_and_keeps_15_percent_overlap():
    text = " ".join(f"w{i}" for i in range(1000))
    with window(190):
        small = chunking.chunk_pages([(1, text)], "lab_report")
        assert (chunking.WINDOW_WORDS, chunking.OVERLAP_WORDS) == (190, 28)
    assert (chunking.WINDOW_WORDS, chunking.OVERLAP_WORDS) == (300, 45)  # restored afterwards
    assert len(small[0].text.split()) == 190
    assert len(small) > len(chunking.chunk_pages([(1, text)], "lab_report"))
