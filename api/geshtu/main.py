"""FastAPI app entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from geshtu import __version__
from geshtu.config import get_settings
from geshtu.logging import configure_logging, get_logger
from geshtu.routes import (
    decisions,
    digest,
    health,
    messages,
    projects,
    search,
    sessions,
    users,
)

_log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    s = get_settings()
    configure_logging(s.log_level)
    _log.info("api_starting", version=__version__, telemetry=s.geshtu_telemetry)
    if s.geshtu_telemetry == "on":
        # Anonymous version-only ping; never blocks startup.
        try:
            from geshtu.telemetry import maybe_send_startup_ping

            maybe_send_startup_ping()
        except Exception as exc:  # noqa: BLE001
            _log.debug("telemetry_skipped", error=str(exc))
    yield
    _log.info("api_stopping")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Geshtu API",
        version=__version__,
        description="Self-hosted shared memory for teams using LLMs.",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(projects.router)
    app.include_router(sessions.router)
    app.include_router(messages.router)
    app.include_router(search.router)
    app.include_router(decisions.router)
    app.include_router(digest.router)
    app.include_router(users.router)
    return app


app = create_app()
