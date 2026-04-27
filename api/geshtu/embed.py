"""Local BGE-M3 embeddings (1024-dim, multilingual, CPU).

Loaded lazily — model download (~2 GB) happens on first call. To
pre-warm in Docker, run `python -m geshtu.embed --warm` after image build.
"""

from __future__ import annotations

import os
import threading
from typing import TYPE_CHECKING

from geshtu.config import get_settings
from geshtu.logging import get_logger

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

_log = get_logger(__name__)

_lock = threading.Lock()
_model: "SentenceTransformer | None" = None


def get_embedder() -> "SentenceTransformer":
    global _model
    if _model is not None:
        return _model
    with _lock:
        if _model is not None:
            return _model
        from sentence_transformers import SentenceTransformer  # heavy import

        s = get_settings()
        cache_dir = os.environ.get("SENTENCE_TRANSFORMERS_HOME", "/app/.model_cache")
        _log.info("loading_embedding_model", model=s.embedding_model, cache_dir=cache_dir)
        _model = SentenceTransformer(
            s.embedding_model,
            cache_folder=cache_dir,
            device="cpu",
        )
        return _model


def embed(text: str) -> list[float]:
    if not text:
        return [0.0] * get_settings().embedding_dim
    vec = get_embedder().encode(
        text,
        normalize_embeddings=True,
        convert_to_numpy=True,
    )
    return vec.tolist()


def embed_batch(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    arr = get_embedder().encode(
        texts,
        normalize_embeddings=True,
        convert_to_numpy=True,
        batch_size=16,
    )
    return [v.tolist() for v in arr]


def main() -> None:
    """Pre-warm the model cache."""
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--warm", action="store_true")
    parser.add_argument("--text", default="hello world")
    args = parser.parse_args()
    vec = embed(args.text)
    print(f"embedding dim={len(vec)} first8={vec[:8]}")


if __name__ == "__main__":
    main()
