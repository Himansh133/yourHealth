"""Download the search models into settings.models_dir.

Default (about 2.9 GB): full-precision bge-m3 embedder + 8-bit reranker, matching the settings' defaults.
--int8 (about 1.2 GB): 8-bit embedder too; set EMBEDDING_MODEL=bge-m3-int8/onnx/model_int8.onnx.

Usage: python -m app.services.chat.download_models [--int8]
"""
import sys

from huggingface_hub import snapshot_download

from app.core.config import settings

RERANKER = ("onnx-community/bge-reranker-v2-m3-ONNX", ["onnx/model_int8.onnx", "*.json"], "bge-reranker-v2-m3")
DEFAULT = [("BAAI/bge-m3", ["onnx/*"], "bge-m3"), RERANKER]
INT8 = [  # less RAM and disk, slightly lower quality
    ("BAAI/bge-m3", ["onnx/tokenizer.json", "onnx/*.model", "onnx/*config.json"], "bge-m3"),
    ("Xenova/bge-m3", ["onnx/model_int8.onnx"], "bge-m3-int8"),
    RERANKER,
]

if __name__ == "__main__":
    for repo, patterns, folder in INT8 if "--int8" in sys.argv else DEFAULT:
        print(snapshot_download(repo, allow_patterns=patterns, local_dir=settings.models_dir / folder), flush=True)
