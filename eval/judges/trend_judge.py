"""LLM judge for trend answers (plan 14.3): which overall direction does an answer state? Fixed prompt, temperature 0,
the same for every system. Keyword matching fails on answers like "fell, then rose; overall up"."""
import hashlib
import json
from pathlib import Path

from app.services.chat.llm import LLMError, get_llm

SYSTEM = """You read an answer about how one lab test changed over time.
What overall direction does the answer say the test moved, from the first value to the last?
Reply with JSON only: {"direction": "up" | "down" | "stable" | "unclear"}.
Use "stable" only if the answer says the values stayed about the same."""


def judge_directions(texts: list[str], cache_file: Path) -> list[str]:
    cache = json.loads(cache_file.read_text()) if cache_file.exists() else {}
    out = []
    for text in texts:
        key = hashlib.sha256(text.encode()).hexdigest()
        if key not in cache:
            try:
                cache[key] = json.loads(get_llm().complete_json(SYSTEM, f"Answer: {text}")).get("direction", "unclear")
            except (LLMError, ValueError):
                cache[key] = "unclear"
        out.append(cache[key])
    cache_file.write_text(json.dumps(cache, indent=1))
    return out
