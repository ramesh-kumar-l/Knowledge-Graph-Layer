"""Response cache — in-memory TTL (dev/test) or Redis when REDIS_URL is set.

Cache singleton is process-local for in-memory backend; shared for Redis backend.
"""
import json
import os
from time import monotonic
from typing import Any

_REDIS_URL = os.getenv("REDIS_URL", "")
_DEFAULT_TTL = 60  # seconds


class _InMemoryCache:
    def __init__(self) -> None:
        self._store: dict[str, tuple[Any, float]] = {}

    async def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        value, expire_at = entry
        if monotonic() > expire_at:
            del self._store[key]
            return None
        return value

    async def set(self, key: str, value: Any, ttl: int = _DEFAULT_TTL) -> None:
        self._store[key] = (value, monotonic() + ttl)

    async def invalidate_prefix(self, prefix: str) -> None:
        for k in [k for k in self._store if k.startswith(prefix)]:
            del self._store[k]

    def size(self) -> int:
        return len(self._store)


class _RedisCache:
    def __init__(self) -> None:
        import redis.asyncio as aioredis  # type: ignore[import]
        self._redis = aioredis.from_url(_REDIS_URL, decode_responses=True)

    async def get(self, key: str) -> Any | None:
        raw = await self._redis.get(key)
        return json.loads(raw) if raw is not None else None

    async def set(self, key: str, value: Any, ttl: int = _DEFAULT_TTL) -> None:
        await self._redis.setex(key, ttl, json.dumps(value, default=str))

    async def invalidate_prefix(self, prefix: str) -> None:
        cursor = 0
        while True:
            cursor, keys = await self._redis.scan(cursor, match=f"{prefix}*", count=100)
            if keys:
                await self._redis.delete(*keys)
            if cursor == 0:
                break


_cache: _InMemoryCache | _RedisCache | None = None


def get_cache() -> _InMemoryCache | _RedisCache:
    global _cache
    if _cache is None:
        if _REDIS_URL:
            try:
                _cache = _RedisCache()
            except Exception:
                _cache = _InMemoryCache()
        else:
            _cache = _InMemoryCache()
    return _cache


def reset_cache() -> None:
    """Reset singleton — for tests only."""
    global _cache
    _cache = None


# ---------------------------------------------------------------------------
# Response cache middleware
# ---------------------------------------------------------------------------

from starlette.middleware.base import BaseHTTPMiddleware  # noqa: E402
from starlette.requests import Request as _Request  # noqa: E402
from starlette.responses import Response as _Response  # noqa: E402

_CACHEABLE_SUFFIXES = ("/graph", "/neighbors")
_CACHE_TTL = 60


def _is_cacheable(path: str) -> bool:
    return (
        path.endswith(_CACHEABLE_SUFFIXES)
        or ("/v1/entities/" in path and "/path/" in path)
        or path.startswith("/v1/explain/")
    )


class CacheMiddleware(BaseHTTPMiddleware):
    """Cache successful GET responses for graph traversal and explain endpoints."""

    async def dispatch(self, request: _Request, call_next) -> _Response:
        if request.method != "GET" or not _is_cacheable(request.url.path):
            return await call_next(request)

        cache = get_cache()
        key = f"r:{request.url.path}:{request.url.query}"
        cached = await cache.get(key)
        if cached is not None:
            return _Response(
                content=cached,
                status_code=200,
                media_type="application/json",
                headers={"X-Cache": "HIT"},
            )

        response = await call_next(request)
        if response.status_code == 200:
            body = b"".join([chunk async for chunk in response.body_iterator])
            await cache.set(key, body.decode("utf-8"), ttl=_CACHE_TTL)
            return _Response(
                content=body,
                status_code=200,
                media_type="application/json",
                headers={"X-Cache": "MISS"},
            )
        return response
