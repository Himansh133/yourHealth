import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_rejects_short_jwt_secret():
    with pytest.raises(ValidationError):
        Settings(jwt_secret="change-me")


def test_accepts_32_byte_jwt_secret():
    assert Settings(jwt_secret="x" * 32).jwt_secret == "x" * 32


def test_default_models_are_full_embedder_and_8bit_reranker():
    s = Settings(jwt_secret="x" * 32)
    assert s.embedding_model == "bge-m3/onnx/model.onnx"
    assert s.reranker_model == "bge-reranker-v2-m3/onnx/model_int8.onnx"
