"""Runtime configuration. Single source of truth, read once at startup."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    database_url: str = Field(..., alias="DATABASE_URL")
    redis_url: str = Field("redis://redis:6379/0", alias="REDIS_URL")

    anthropic_api_key: str = Field(..., alias="ANTHROPIC_API_KEY")
    extraction_model: str = Field("claude-haiku-4-5", alias="EXTRACTION_MODEL")
    digest_model: str = Field("claude-sonnet-4-6", alias="DIGEST_MODEL")
    embedding_model: str = Field("BAAI/bge-m3", alias="EMBEDDING_MODEL")
    embedding_dim: int = Field(1024, alias="EMBEDDING_DIM")

    jwt_secret: str = Field(..., alias="JWT_SECRET")
    jwt_algorithm: str = Field("HS256", alias="JWT_ALGORITHM")
    jwt_default_ttl_days: int = Field(365, alias="JWT_DEFAULT_TTL_DAYS")

    public_hostname: str = Field("localhost", alias="PUBLIC_HOSTNAME")
    log_level: str = Field("info", alias="LOG_LEVEL")

    messages_retention_days: int = Field(0, alias="MESSAGES_RETENTION_DAYS")
    geshtu_telemetry: str = Field("off", alias="GESHTU_TELEMETRY")

    digest_cache_ttl_seconds: int = Field(3600, alias="DIGEST_CACHE_TTL_SECONDS")
    extraction_min_chars: int = Field(40, alias="EXTRACTION_MIN_CHARS")

    # Dedup thresholds (spec §5.1)
    dedup_supersede_threshold: float = Field(0.92, alias="DEDUP_SUPERSEDE_THRESHOLD")
    dedup_refine_threshold: float = Field(0.75, alias="DEDUP_REFINE_THRESHOLD")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
