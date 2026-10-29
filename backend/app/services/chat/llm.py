"""LLM behind one small interface (plan 5.1): swap providers for evals, use a fake in tests.

The provider is any OpenAI-compatible chat API. We use GMI Cloud (https://api.gmi-serving.com/v1).
"""
from typing import Protocol

import httpx

from app.core.config import settings


class LLMError(Exception):
    pass


class LLM(Protocol):
    def complete_json(self, system: str, user: str) -> str: ...


class FakeLLM:
    """Returns scripted replies in order; keeps the prompts it was given."""

    def __init__(self, replies: list[str]):
        self.replies = list(replies)
        self.prompts: list[tuple[str, str]] = []

    def complete_json(self, system: str, user: str) -> str:
        self.prompts.append((system, user))
        return self.replies.pop(0)


class OpenAICompatibleLLM:
    def __init__(self, base_url: str, api_key: str, model: str, timeout: float = 60,
                 transport: httpx.BaseTransport | None = None):
        self.model = model
        self._client = httpx.Client(base_url=base_url.rstrip("/") + "/", timeout=timeout, transport=transport,
                                    headers={"Authorization": f"Bearer {api_key}"})

    def complete_json(self, system: str, user: str) -> str:
        body = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "response_format": {"type": "json_object"},
            "temperature": 0,
        }
        try:
            resp = self._client.post("chat/completions", json=body)
        except httpx.HTTPError as e:
            raise LLMError(f"LLM request failed: {type(e).__name__}") from e
        if resp.status_code != 200:
            raise LLMError(f"LLM provider returned {resp.status_code}")
        return resp.json()["choices"][0]["message"]["content"]


def get_llm() -> LLM:
    if not (settings.llm_api_key and settings.llm_model):
        raise LLMError("LLM is not configured: set LLM_API_KEY and LLM_MODEL")
    return OpenAICompatibleLLM(settings.llm_base_url, settings.llm_api_key, settings.llm_model)


class _Unavailable:
    def complete_json(self, system: str, user: str) -> str:
        raise LLMError("LLM is not configured")


def get_llm_or_unavailable() -> LLM:
    """Without a configured LLM, answers fall back to the table of retrieved facts."""
    try:
        return get_llm()
    except LLMError:
        return _Unavailable()
