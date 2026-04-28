FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_HOME=/app/.model_cache \
    SENTENCE_TRANSFORMERS_HOME=/app/.model_cache \
    TRANSFORMERS_OFFLINE=0

# Build deps for psycopg, sentence-transformers, etc.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Two-stage copy: pull declared deps from pyproject before code is in place
# (so `docker build` cache hits when only Python source changes), then copy
# the package and register it in editable mode without re-resolving deps.
COPY pyproject.toml ./

# Install CPU-only PyTorch from pytorch.org's dedicated index FIRST. Default
# `pip install torch` from PyPI silently pulls ~2.5 GB of nvidia-* CUDA
# wheels — useless on a CPU-only deployment, but they bloat the image to
# ~3 GB. The CPU wheel is ~200 MB and is functionally identical for our
# inference workload (BGE-M3 sentence embeddings, no GPU).
RUN pip install --upgrade pip \
 && pip install --index-url https://download.pytorch.org/whl/cpu \
        "torch>=2.2"

# Now everything else from the regular PyPI index. sentence-transformers
# already finds the CPU torch we just installed and won't try to "fix" it.
RUN pip install \
        "fastapi>=0.115" "uvicorn[standard]>=0.30" \
        "pydantic>=2.7" "pydantic-settings>=2.4" \
        "sqlalchemy>=2.0" "psycopg[binary,pool]>=3.2" "pgvector>=0.3" \
        "celery[redis]>=5.4" "redis>=5.0" \
        "anthropic>=0.40" \
        "sentence-transformers>=3.0" "numpy>=1.26" \
        "PyJWT>=2.9" "bcrypt>=4.2" "python-multipart>=0.0.9" \
        "httpx>=0.27" "click>=8.1" "structlog>=24.1" "email-validator>=2.2"

COPY geshtu ./geshtu
RUN pip install -e . --no-deps && mkdir -p /app/.model_cache

EXPOSE 8000

CMD ["uvicorn", "geshtu.main:app", "--host", "0.0.0.0", "--port", "8000"]
