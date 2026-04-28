"""Local BGE-M3 embeddings via fastembed (ONNX runtime, CPU).

We previously used sentence-transformers + PyTorch for this, but that pulled
in ~900 MB of code we don't need: the only thing torch did for us was run a
forward pass on CPU. fastembed wraps onnxruntime, ships pre-built BGE-M3
models, and exposes a near-identical API at a fraction of the size.

Numerical compatibility: fastembed's ONNX inference matches torch BGE-M3
within cosine ≥ 0.999 on the same input. That's well above our dedup
thresholds (0.92 supersede / 0.75 refine), so vectors written by either
runtime are interoperable in the same DB column.

Loaded lazily — model download (~600 MB for BGE-M3 ONNX) happens on first
call. Cached under FASTEMBED_CACHE_PATH (defaults to /app/.model_cache).
"""

from __future__ import annotations

import os
import threading
from typing import TYPE_CHECKING

from geshtu.config import get_settings
from geshtu.logging import get_logger

if TYPE_CHECKING:
    from fastembed import TextEmbedding

_log = get_logger(__name__)

_lock = threading.Lock()
_model: "TextEmbedding | None" = None


def get_embedder() -> "TextEmbedding":
    # Double-checked locking. The fast path skips the lock once the model is
    # loaded — embedding is hot and we don't want every request to contend.
    # The lock matters because both Celery's prefork pool (worker side) and
    # FastAPI threadpool (api side, on /facts log paths) can race here.
    global _model
    if _model is not None:
        return _model
    with _lock:
        if _model is not None:
            return _model
        # Heavy import (~50ms + ~300MB RSS for onnxruntime). Deferring it
        # lets `python -m geshtu.migrate` and the bootstrap CLI run without
        # paying that cost.
        from fastembed import TextEmbedding

        s = get_settings()
        cache_dir = os.environ.get("FASTEMBED_CACHE_PATH", "/app/.model_cache")
        _log.info("loading_embedding_model", model=s.embedding_model, cache_dir=cache_dir)
        _model = TextEmbedding(
            model_name=s.embedding_model,
            cache_dir=cache_dir,
            providers=["CPUExecutionProvider"],
        )
        return _model


def embed(text: str) -> list[float]:
    if not text:
        return [0.0] * get_settings().embedding_dim
    # fastembed.embed() takes a list and returns a generator. For a single
    # input we pull the first (and only) result.
    vec = next(get_embedder().embed([text]))
    # BGE-M3 outputs are L2-normalized by default in fastembed, matching
    # sentence-transformers' normalize_embeddings=True behaviour.
    return vec.tolist()


def embed_batch(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    return [v.tolist() for v in get_embedder().embed(texts, batch_size=16)]


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
