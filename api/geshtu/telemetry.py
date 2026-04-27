"""Anonymous startup ping (spec §15.6.4). Off by default, opt-in via env."""

from __future__ import annotations

import platform
import uuid

import httpx

from geshtu import __version__
from geshtu.config import get_settings
from geshtu.logging import get_logger

_log = get_logger(__name__)
_INSTANCE_ID = str(uuid.uuid4())  # regenerated per process — no persistent ID


def maybe_send_startup_ping() -> None:
    s = get_settings()
    if s.geshtu_telemetry != "on":
        return
    payload = {
        "version": __version__,
        "instance_id": _INSTANCE_ID,
        "platform": f"{platform.system().lower()}/{platform.machine()}",
    }
    try:
        with httpx.Client(timeout=2.0) as c:
            c.post("https://telemetry.geshtu.io/v1/started", json=payload)
        _log.debug("telemetry_sent")
    except Exception as exc:  # noqa: BLE001
        _log.debug("telemetry_failed", error=str(exc))
