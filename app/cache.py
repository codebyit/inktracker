from __future__ import annotations

import json
import logging
import os
from typing import Any, Callable

import redis

log = logging.getLogger(__name__)

_client: redis.Redis | None = None


def _redis_url() -> str | None:
    return os.environ.get("REDIS_URL")


def _get_client() -> redis.Redis | None:
    global _client
    url = _redis_url()
    if not url:
        return None
    if _client is not None:
        return _client
    try:
        _client = redis.Redis.from_url(url, decode_responses=True)
        _client.ping()
        return _client
    except Exception as exc:
        log.warning("Redis unavailable, caching disabled: %s", exc)
        _client = None
        return None


def get_json(key: str) -> Any | None:
    client = _get_client()
    if client is None:
        return None
    try:
        raw = client.get(key)
        if raw is None:
            return None
        return json.loads(raw)
    except Exception as exc:
        log.warning("Redis get failed for key %s: %s", key, exc)
        return None


def set_json(key: str, value: Any, ttl_seconds: int) -> None:
    client = _get_client()
    if client is None:
        return
    try:
        client.setex(key, ttl_seconds, json.dumps(value, ensure_ascii=True))
    except Exception as exc:
        log.warning("Redis set failed for key %s: %s", key, exc)


def get_or_set_json(key: str, ttl_seconds: int, producer: Callable[[], Any]) -> Any:
    cached = get_json(key)
    if cached is not None:
        return cached
    value = producer()
    set_json(key, value, ttl_seconds)
    return value


def invalidate_prefixes(prefixes: list[str]) -> None:
    client = _get_client()
    if client is None:
        return
    try:
        for prefix in prefixes:
            keys = client.keys(f"{prefix}*")
            if keys:
                client.delete(*keys)
    except Exception as exc:
        log.warning("Redis invalidation failed: %s", exc)


def invalidate_dashboard_analytics_cache() -> None:
    invalidate_prefixes([
        "dashboard:",
        "analytics:",
        "settings_json:",
    ])
