"""Split document text into chunks for search (plan 7.5).

Window sizes are in words, about 400 and 60 tokens. Lab values are not chunked: value questions go to SQL.
"""
import re
from dataclasses import dataclass

CHUNKER_VERSION = "chunk-v2"
WINDOW_WORDS = 300
OVERLAP_WORDS = 45

_HEADINGS = [
    "diagnosis", "final diagnosis", "provisional diagnosis", "chief complaints?", "presenting complaints?",
    "history", "history of present illness", "past history", "course in (?:the )?hospital", "hospital course",
    "investigations?", "treatment(?: given)?", "procedures?(?: done)?", "condition (?:at|on) discharge",
    "advice on discharge", "discharge advice", "advice", "(?:discharge )?medications?(?: on discharge)?",
    "follow[ -]?up",
]
_HEADING_RE = re.compile(rf"^(?:{'|'.join(_HEADINGS)})\s*(?::.*)?$", re.IGNORECASE)


@dataclass(frozen=True)
class ChunkSpec:
    chunk_type: str  # page_text | section
    page_start: int
    page_end: int
    text: str


def chunk_pages(pages: list[tuple[int, str]], doc_type: str) -> list[ChunkSpec]:
    chunks = [ChunkSpec("page_text", no, no, t) for no, text in pages for t in _windows(text.split())]
    if doc_type == "discharge":
        chunks += _sections(pages)
    return chunks


def _windows(words: list[str]) -> list[str]:
    if not words:
        return []
    step = WINDOW_WORDS - OVERLAP_WORDS
    starts = range(0, max(len(words) - OVERLAP_WORDS, 1), step)
    return [" ".join(words[s:s + WINDOW_WORDS]) for s in starts]


def _sections(pages: list[tuple[int, str]]) -> list[ChunkSpec]:
    """Text from each recognised heading to the next one, which may run across pages."""
    sections: list[list[tuple[int, str]]] = []  # page number for each line
    for page_no, text in pages:
        for line in (ln.strip() for ln in text.splitlines()):
            if not line:
                continue
            if _HEADING_RE.match(line):
                sections.append([(page_no, line)])
            elif sections:
                sections[-1].append((page_no, line))
    chunks = []
    for lines in sections:
        tagged = [(page, word) for page, line in lines for word in line.split()]
        if len(tagged) <= WINDOW_WORDS:
            chunks.append(ChunkSpec("section", lines[0][0], lines[-1][0], "\n".join(line for _, line in lines)))
            continue
        for start in range(0, max(len(tagged) - OVERLAP_WORDS, 1), WINDOW_WORDS - OVERLAP_WORDS):
            part = tagged[start:start + WINDOW_WORDS]
            chunks.append(ChunkSpec("section", part[0][0], part[-1][0], " ".join(word for _, word in part)))
    return chunks
