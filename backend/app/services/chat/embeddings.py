"""Embedding model and reranker behind small interfaces (plan 5.1, 10.5), with stand-ins in tests.

Both run as ONNX on the CPU through onnxruntime (already used for OCR), so no PyTorch.
"""
from functools import lru_cache
from pathlib import Path
from typing import Protocol

import numpy as np

from app.core.config import settings


class Embedder(Protocol):
    name: str

    def embed(self, texts: list[str]) -> list[list[float]]: ...  # unit-length vectors


class Reranker(Protocol):
    def score(self, query: str, passages: list[str]) -> list[float]: ...  # 0..1, higher is more relevant


MAX_TOKENS = 1024  # chunks are about 300 words; bge-m3 allows 8192, but CPU time grows with length
BATCH = 8


class _OnnxModel:
    def __init__(self, model_path: Path, tokenizer_path: Path):
        import onnxruntime as ort  # heavy import: only processes that use the models pay for it
        from tokenizers import Tokenizer

        self.session = ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])
        self.inputs = {i.name for i in self.session.get_inputs()}
        self.tokenizer = Tokenizer.from_file(str(tokenizer_path))
        self.tokenizer.enable_truncation(MAX_TOKENS)
        pad = self.tokenizer.token_to_id("<pad>")  # XLM-RoBERTa pads with id 1, not the library's default 0
        if pad is None:
            self.tokenizer.enable_padding()
        else:
            self.tokenizer.enable_padding(pad_id=pad, pad_token="<pad>")

    def run(self, encodings) -> dict[str, np.ndarray]:
        feed = {"input_ids": np.array([e.ids for e in encodings], dtype=np.int64),
                "attention_mask": np.array([e.attention_mask for e in encodings], dtype=np.int64)}
        if "token_type_ids" in self.inputs:
            feed["token_type_ids"] = np.zeros_like(feed["input_ids"])
        names = [o.name for o in self.session.get_outputs()]
        return dict(zip(names, self.session.run(None, {k: v for k, v in feed.items() if k in self.inputs})))


class OnnxEmbedder(_OnnxModel):
    """bge-m3 dense vectors: the [CLS] token's hidden state, scaled to unit length."""

    def __init__(self, model_path: Path, tokenizer_path: Path, name: str):
        super().__init__(model_path, tokenizer_path)
        self.name = name

    def embed(self, texts: list[str]) -> list[list[float]]:
        out = []
        for i in range(0, len(texts), BATCH):
            result = self.run(self.tokenizer.encode_batch(texts[i:i + BATCH]))
            vectors = result["dense_vecs"] if "dense_vecs" in result else next(iter(result.values()))[:, 0]
            vectors = vectors / np.linalg.norm(vectors, axis=1, keepdims=True)
            out += vectors.tolist()
        return out


class OnnxReranker(_OnnxModel):
    """bge-reranker-v2-m3: a relevance logit per (question, passage) pair, as a probability."""

    def score(self, query: str, passages: list[str]) -> list[float]:
        out = []
        for i in range(0, len(passages), BATCH):
            result = self.run(self.tokenizer.encode_batch([(query, p) for p in passages[i:i + BATCH]]))
            logits = next(iter(result.values())).reshape(-1)
            out += (1 / (1 + np.exp(-logits))).tolist()
        return out


@lru_cache
def get_embedder() -> Embedder | None:
    model, tokenizer = settings.models_dir / settings.embedding_model, settings.models_dir / settings.embedding_tokenizer
    if not settings.embeddings_enabled or not (model.exists() and tokenizer.exists()):
        return None
    return OnnxEmbedder(model, tokenizer, name=f"bge-m3:{model.name}")


@lru_cache
def get_reranker() -> Reranker | None:
    model, tokenizer = settings.models_dir / settings.reranker_model, settings.models_dir / settings.reranker_tokenizer
    if not settings.embeddings_enabled or not (model.exists() and tokenizer.exists()):
        return None
    return OnnxReranker(model, tokenizer)
