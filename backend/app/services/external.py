"""Integrasi layanan eksternal: kurs mata uang dan webhook n8n."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import httpx

from ..config import settings

logger = logging.getLogger("ruangkarya.external")

FALLBACK_RATE = 0.00006
_cache: dict[str, Any] = {"value": None, "expires": 0.0}
_lock = asyncio.Lock()


def get_cached_rate() -> float | None:
    value = _cache["value"]
    if value is not None and _cache["expires"] > time.time():
        return float(value)
    return None


async def fetch_exchange_rate() -> float:
    """Ambil kurs IDR ke USD dengan timeout dan fallback."""
    fresh = get_cached_rate()
    if fresh is not None:
        return fresh
    async with _lock:
        fresh = get_cached_rate()
        if fresh is not None:
            return fresh
        timeout = settings.exchange_rate_timeout_ms / 1000
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(settings.exchange_rate_url)
                response.raise_for_status()
                payload = response.json()
            value = float(payload.get("rates", {}).get("USD") or FALLBACK_RATE)
            ttl = settings.exchange_rate_ttl_minutes * 60
        except Exception as error:  # noqa: BLE001 - fallback disengaja
            logger.warning("Kurs eksternal gagal: %s", error)
            value = FALLBACK_RATE
            ttl = 300
        _cache["value"] = value
        _cache["expires"] = time.time() + ttl
        return value


def refresh_rate_in_background() -> None:
    """Perbarui kurs tanpa memblokir request yang sedang berjalan."""
    if get_cached_rate() is not None:
        return
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    loop.create_task(fetch_exchange_rate())


async def notify_n8n(payload: dict[str, Any], url: str | None = None) -> dict[str, Any]:
    target = url or settings.n8n_webhook_url
    if not target:
        return {"sent": False, "reason": "N8N_WEBHOOK_URL belum diatur"}
    timeout = settings.n8n_timeout_ms / 1000
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(target, json=payload)
        return {"sent": response.is_success, "status": response.status_code}
    except Exception as error:  # noqa: BLE001 - notifikasi bersifat opsional
        logger.warning("Webhook n8n gagal: %s", error)
        return {"sent": False, "reason": str(error)}
