"""Download the search models into settings.models_dir (about 4.6 GB, or 1.2 GB with --int8).

Usage: python -m app.services.chat.download_models [--int8]
"""
import sys

from huggingface_hub import snapshot_download

from app.core.config import settings

FULL = [
    ("BAAI/bge-m3", ["onnx/*"], "bge-m3"),
    ("onnx-community/bge-reranker-v2-m3-ONNX", ["onnx/model.onnx", "onnx/model.onnx_data", "*.json"],
     "bge-reranker-v2-m3"),
]
INT8 = [  # less RAM and disk, slightly lower quality; set EMBEDDING_MODEL / RERANKER_MODEL to these files
    ("BAAI/bge-m3", ["onnx/tokenizer.json", "onnx/*.model", "onnx/*config.json"], "bge-m3"),
    ("Xenova/bge-m3", ["onnx/model_int8.onnx"], "bge-m3-int8"),
    ("onnx-community/bge-reranker-v2-m3-ONNX", ["onnx/model_int8.onnx", "*.json"], "bge-reranker-v2-m3"),
]

if __name__ == "__main__":
    for repo, patterns, folder in INT8 if "--int8" in sys.argv else FULL:
        print(snapshot_download(repo, allow_patterns=patterns, local_dir=settings.models_dir / folder), flush=True)
