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

COPY pyproject.toml ./
RUN pip install --upgrade pip && pip install -e .

COPY geshtu ./geshtu
RUN mkdir -p /app/.model_cache

EXPOSE 8000

CMD ["uvicorn", "geshtu.main:app", "--host", "0.0.0.0", "--port", "8000"]
