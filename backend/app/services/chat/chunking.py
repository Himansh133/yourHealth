"""Split document text into chunks for search (plan 7.5).

Window sizes are in words, about 400 and 60 tokens. Lab values are not chunked: value questions go to SQL.
"""
import re
from dataclasses import dataclass

CHUNKER_VERSION = "chunk-v1"
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
    sections: list[tuple[int, int, list[str]]] = []  # (page_start, page_end, lines)
    for page_no, text in pages:
        for line in (ln.strip() for ln in text.splitlines()):
            if not line:
                continue
            if _HEADING_RE.match(line):
                sections.append((page_no, page_no, [line]))
            elif sections:
                start, _, lines = sections[-1]
                lines.append(line)
                sections[-1] = (start, page_no, lines)
    return [ChunkSpec("section", start, end, "\n".join(lines)) for start, end, lines in sections]
