# ─── Stage 1: builder ────────────────────────────────────────────────
# Has gcc + libpq-dev for any wheel without a manylinux binary.
# CPU-only PyTorch comes from pytorch.org's dedicated CPU index — saves
# ~6 GB of nvidia-* CUDA wheels that PyPI's default torch silently pulls.

FROM python:3.12-slim AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml ./

RUN pip install --upgrade pip \
 && pip install --index-url https://download.pytorch.org/whl/cpu \
        "torch>=2.2"

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

# Trim install-time cruft. Bytecode caches regenerate; tests/docs inside
# wheels aren't imported. Saves ~80 MB.
RUN find /usr/local/lib/python3.12/site-packages -type d -name "__pycache__" -prune -exec rm -rf {} + \
 && find /usr/local/lib/python3.12/site-packages -type d -name "tests" -prune -exec rm -rf {} + \
 && find /usr/local/lib/python3.12/site-packages -type d -name "test" -prune -exec rm -rf {} + \
 && find /usr/local/lib/python3.12/site-packages -name "*.pyc" -delete \
 && find /usr/local/lib/python3.12/site-packages -name "*.pyo" -delete


# ─── Stage 2: runtime ────────────────────────────────────────────────
# Slim image with only what's needed at runtime: Python stdlib, the
# installed packages, our package source, and the model cache directory.
# No compilers, no headers, no apt cache.

FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HF_HOME=/app/.model_cache \
    SENTENCE_TRANSFORMERS_HOME=/app/.model_cache \
    TRANSFORMERS_OFFLINE=0

WORKDIR /app

# psycopg[binary] ships libpq statically — no libpq5 needed at runtime.
COPY --from=builder /usr/local/lib/python3.12 /usr/local/lib/python3.12
COPY --from=builder /usr/local/bin/uvicorn /usr/local/bin/uvicorn
COPY --from=builder /usr/local/bin/celery /usr/local/bin/celery
COPY --from=builder /app /app

EXPOSE 8000

CMD ["uvicorn", "geshtu.main:app", "--host", "0.0.0.0", "--port", "8000"]
