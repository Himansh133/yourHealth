"""Embedding model and reranker behind small interfaces (plan 5.1, 10.5), with stand-ins in tests."""
from typing import Protocol


class Embedder(Protocol):
    name: str

    def embed(self, texts: list[str]) -> list[list[float]]: ...  # unit-length vectors


class Reranker(Protocol):
    def score(self, query: str, passages: list[str]) -> list[float]: ...  # 0..1, higher is more relevant
