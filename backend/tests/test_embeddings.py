from app.core.config import settings
from app.services.chat import embeddings


def test_models_are_off_in_tests():
    # conftest switches them off, so no test loads gigabytes of model
    assert settings.embeddings_enabled is False
    assert embeddings.get_embedder() is None
    assert embeddings.get_reranker() is None


def test_missing_model_files_mean_no_model(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "embeddings_enabled", True)
    monkeypatch.setattr(settings, "models_dir", tmp_path)
    embeddings.get_embedder.cache_clear()
    embeddings.get_reranker.cache_clear()
    try:
        assert embeddings.get_embedder() is None
        assert embeddings.get_reranker() is None
    finally:
        embeddings.get_embedder.cache_clear()
        embeddings.get_reranker.cache_clear()
