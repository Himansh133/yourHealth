"""Chunk-size ablation (plan 14.4): rebuild an eval database's search chunks with another window size.

The app's window is 300 words (about 400 tokens); the plan compares about 250 / 400 / 600 tokens, i.e. 190 / 300 /
450 words. Always finish with --words 300 to put the database back. Usage (from backend/):
  DATABASE_URL=postgresql+psycopg://yourhealth:yourhealth@localhost:5432/yourhealth_eval_v2 \\
    PYTHONPATH=.. .venv/bin/python -m eval.runners.rechunk --words 190
"""
import argparse
import sys
from contextlib import contextmanager

from app.core.config import settings
from app.services.chat import chunking

OVERLAP_SHARE = 0.15  # 45 of 300 words, as in the app


@contextmanager
def window(words: int):
    saved = chunking.WINDOW_WORDS, chunking.OVERLAP_WORDS
    chunking.WINDOW_WORDS, chunking.OVERLAP_WORDS = words, round(words * OVERLAP_SHARE)
    try:
        yield
    finally:
        chunking.WINDOW_WORDS, chunking.OVERLAP_WORDS = saved


def main(words: int) -> None:
    from app.db.session import SessionLocal
    from app.workers.reindex import reindex_all
    from eval.runners.load_eval_db import EVAL_DB
    if not EVAL_DB.search(settings.database_url):
        sys.exit("Refusing: DATABASE_URL must point at an eval database (yourhealth_eval...)")
    with window(words), SessionLocal() as db:
        print(f"re-chunked {reindex_all(db)} documents with {words}-word windows")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--words", type=int, required=True)
    main(ap.parse_args().words)
