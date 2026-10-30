from app.services.chat.chunking import OVERLAP_WORDS, WINDOW_WORDS, chunk_pages


def words(n, prefix="w"):
    return " ".join(f"{prefix}{i}" for i in range(n))


def test_short_page_is_one_chunk():
    [c] = chunk_pages([(1, "Patient is stable. Advised low salt diet.")], "other")
    assert (c.chunk_type, c.page_start, c.page_end, c.text) == ("page_text", 1, 1, "Patient is stable. Advised low salt diet.")


def test_long_page_is_split_into_overlapping_windows():
    chunks = chunk_pages([(1, words(WINDOW_WORDS + 100))], "other")
    assert len(chunks) == 2
    first, second = (c.text.split() for c in chunks)
    assert len(first) == WINDOW_WORDS
    assert first[-OVERLAP_WORDS:] == second[:OVERLAP_WORDS]
    assert second[-1] == f"w{WINDOW_WORDS + 99}"


def test_chunks_never_cross_pages():
    chunks = chunk_pages([(1, "page one text"), (2, "page two text")], "other")
    assert [(c.page_start, c.page_end, c.text) for c in chunks] == [(1, 1, "page one text"), (2, 2, "page two text")]


def test_blank_pages_make_no_chunks():
    assert chunk_pages([(1, "   \n ")], "other") == []


def test_discharge_summary_also_gets_section_chunks_across_pages():
    pages = [
        (1, "City Hospital\nDiagnosis:\nType 2 diabetes mellitus\nCourse in Hospital\nTreated with insulin."),
        (2, "Patient improved.\nAdvice on Discharge:\nLow sugar diet, walk daily.\nFollow up in 2 weeks."),
    ]
    sections = [c for c in chunk_pages(pages, "discharge") if c.chunk_type == "section"]
    assert [(c.text.splitlines()[0], c.page_start, c.page_end) for c in sections] == [
        ("Diagnosis:", 1, 1),
        ("Course in Hospital", 1, 2),
        ("Advice on Discharge:", 2, 2),
    ]
    assert "Low sugar diet" in sections[2].text
    assert "Treated with insulin.\nPatient improved." in sections[1].text


def test_other_documents_get_no_section_chunks():
    pages = [(1, "Diagnosis:\nSomething")]
    assert {c.chunk_type for c in chunk_pages(pages, "lab_report")} == {"page_text"}


def test_long_sections_are_bounded_and_cite_only_pages_in_each_window():
    pages = [(1, 'Course in Hospital\n' + words(400, 'a')), (2, words(400, 'b'))]
    sections = [c for c in chunk_pages(pages, 'discharge') if c.chunk_type == 'section']
    assert len(sections) > 1
    assert all(len(c.text.split()) <= WINDOW_WORDS for c in sections)
    assert (sections[0].page_start, sections[0].page_end) == (1, 1)
    assert (sections[-1].page_start, sections[-1].page_end) == (2, 2)
    for left, right in zip(sections, sections[1:]):
        assert left.text.split()[-OVERLAP_WORDS:] == right.text.split()[:OVERLAP_WORDS]
    combined = ' '.join(c.text for c in sections).split()
    assert all(f'{prefix}{i}' in combined for prefix in ('a', 'b') for i in range(400))
