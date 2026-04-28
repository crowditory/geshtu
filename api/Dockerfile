# ─── Stage 1: builder ────────────────────────────────────────────────
# Has gcc + libpq-dev to compile any wheel that doesn't ship a manylinux
# binary (rare in 2026 but still happens). The final image won't carry
# any of these — see the runtime stage below.

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

# Install runtime Python deps. fastembed (with onnxruntime) replaces the
# torch + sentence-transformers stack, saving ~900 MB. psycopg[binary]
# ships libpq statically, so the runtime stage doesn't need libpq5.
RUN pip install --upgrade pip \
 && pip install \
        "fastapi>=0.115" "uvicorn[standard]>=0.30" \
        "pydantic>=2.7" "pydantic-settings>=2.4" \
        "sqlalchemy>=2.0" "psycopg[binary,pool]>=3.2" "pgvector>=0.3" \
        "celery[redis]>=5.4" "redis>=5.0" \
        "anthropic>=0.40" \
        "fastembed>=0.4" "numpy>=1.26" \
        "PyJWT>=2.9" "bcrypt>=4.2" "python-multipart>=0.0.9" \
        "httpx>=0.27" "click>=8.1" "structlog>=24.1" "email-validator>=2.2"

COPY geshtu ./geshtu
RUN pip install -e . --no-deps && mkdir -p /app/.model_cache

# Trim install-time cruft that's safe to drop at runtime: bytecode caches
# get regenerated, tests/docs inside packages aren't imported. Saves ~80 MB.
RUN find /usr/local/lib/python3.12/site-packages -type d -name "__pycache__" -prune -exec rm -rf {} + \
 && find /usr/local/lib/python3.12/site-packages -type d -name "tests" -prune -exec rm -rf {} + \
 && find /usr/local/lib/python3.12/site-packages -type d -name "test" -prune -exec rm -rf {} + \
 && find /usr/local/lib/python3.12/site-packages -name "*.pyc" -delete \
 && find /usr/local/lib/python3.12/site-packages -name "*.pyo" -delete


# ─── Stage 2: runtime ────────────────────────────────────────────────
# Slim image with only what the API and worker need at runtime: Python
# stdlib, the installed packages, our package source, and the model cache
# directory. No compilers, no headers, no apt cache.

FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HF_HOME=/app/.model_cache \
    FASTEMBED_CACHE_PATH=/app/.model_cache

WORKDIR /app

# Copy installed Python packages and any console scripts (uvicorn, celery)
# from the builder. Our editable-install of `geshtu` lives at /app/geshtu
# with metadata pointing to that absolute path — the path matches across
# stages, so the editable install keeps working.
COPY --from=builder /usr/local/lib/python3.12 /usr/local/lib/python3.12
COPY --from=builder /usr/local/bin/uvicorn /usr/local/bin/uvicorn
COPY --from=builder /usr/local/bin/celery /usr/local/bin/celery
COPY --from=builder /app /app

EXPOSE 8000

CMD ["uvicorn", "geshtu.main:app", "--host", "0.0.0.0", "--port", "8000"]
