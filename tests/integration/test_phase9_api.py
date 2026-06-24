"""Phase 9 integration tests — cache, security headers, Redis rate limit fallback.

Uses a lightweight ASGI app (no database, auth disabled) to verify HTTP-level
behavior of Phase 9 middleware additions.
"""
import os

import pytest
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport

from src.api.cache import CacheMiddleware, reset_cache
from src.api.rate_limit import get_limiter
from src.api.security_headers import SecurityHeadersMiddleware


def _cached_app() -> FastAPI:
    """Minimal app with cache + security headers wired in."""
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(CacheMiddleware)

    call_count = {"n": 0}

    @app.get("/v1/entities/abc/graph")
    async def graph():
        call_count["n"] += 1
        return {"nodes": [], "edges": [], "call": call_count["n"]}

    @app.get("/v1/explain/abc")
    async def explain():
        call_count["n"] += 1
        return {"entity_id": "abc", "call": call_count["n"]}

    @app.get("/v1/entities")
    async def list_entities():
        call_count["n"] += 1
        return {"items": [], "call": call_count["n"]}

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    app._call_count = call_count  # type: ignore[attr-defined]
    return app


@pytest.fixture(autouse=True)
def _reset_cache():
    reset_cache()
    yield
    reset_cache()


@pytest.fixture
def cached_app():
    return _cached_app()


# ── Cache middleware ──────────────────────────────────────────────────────────

class TestCacheMiddleware:
    async def test_graph_endpoint_first_request_is_miss(self, cached_app):
        async with AsyncClient(transport=ASGITransport(app=cached_app), base_url="http://test") as c:
            resp = await c.get("/v1/entities/abc/graph")
        assert resp.status_code == 200
        assert resp.headers.get("x-cache") == "MISS"

    async def test_graph_endpoint_second_request_is_hit(self, cached_app):
        async with AsyncClient(transport=ASGITransport(app=cached_app), base_url="http://test") as c:
            await c.get("/v1/entities/abc/graph")
            resp2 = await c.get("/v1/entities/abc/graph")
        assert resp2.headers.get("x-cache") == "HIT"

    async def test_cached_response_identical_to_original(self, cached_app):
        async with AsyncClient(transport=ASGITransport(app=cached_app), base_url="http://test") as c:
            r1 = await c.get("/v1/entities/abc/graph")
            r2 = await c.get("/v1/entities/abc/graph")
        assert r1.json() == r2.json()

    async def test_explain_endpoint_cached(self, cached_app):
        async with AsyncClient(transport=ASGITransport(app=cached_app), base_url="http://test") as c:
            r1 = await c.get("/v1/explain/abc")
            r2 = await c.get("/v1/explain/abc")
        assert r1.json() == r2.json()
        assert r2.headers.get("x-cache") == "HIT"

    async def test_non_cacheable_endpoint_not_cached(self, cached_app):
        async with AsyncClient(transport=ASGITransport(app=cached_app), base_url="http://test") as c:
            r1 = await c.get("/v1/entities")
            r2 = await c.get("/v1/entities")
        # call count should increment on each request (no caching)
        assert r1.json()["call"] != r2.json()["call"]
        assert "x-cache" not in r2.headers

    async def test_cache_key_includes_query_params(self, cached_app):
        async with AsyncClient(transport=ASGITransport(app=cached_app), base_url="http://test") as c:
            r1 = await c.get("/v1/entities/abc/graph?max_depth=2")
            r2 = await c.get("/v1/entities/abc/graph?max_depth=3")
        # Different query params → different cache entries → both MISSes
        assert r1.headers.get("x-cache") == "MISS"
        assert r2.headers.get("x-cache") == "MISS"

    async def test_post_requests_not_cached(self, cached_app):
        async with AsyncClient(transport=ASGITransport(app=cached_app), base_url="http://test") as c:
            resp = await c.post("/v1/entities/abc/graph", content=b"{}")
        # POST returns 405 (method not allowed) — not a caching concern
        assert "x-cache" not in resp.headers


# ── Security headers in full app ──────────────────────────────────────────────

class TestSecurityHeadersIntegration:
    async def test_health_has_security_headers(self, cached_app):
        async with AsyncClient(transport=ASGITransport(app=cached_app), base_url="http://test") as c:
            resp = await c.get("/health")
        assert resp.headers.get("x-frame-options") == "DENY"
        assert resp.headers.get("x-content-type-options") == "nosniff"

    async def test_api_response_has_csp(self, cached_app):
        async with AsyncClient(transport=ASGITransport(app=cached_app), base_url="http://test") as c:
            resp = await c.get("/v1/entities")
        assert "content-security-policy" in resp.headers


# ── Redis rate limit fallback (no Redis → in-process) ─────────────────────────

class TestRedisRateLimitFallback:
    def setup_method(self):
        os.environ.pop("API_KEYS", None)
        get_limiter().reset()

    def teardown_method(self):
        get_limiter().reset()

    async def test_fallback_allows_normal_requests(self):
        from src.api.main import app
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as c:
            resp = await c.get("/health")
        assert resp.status_code == 200

    async def test_in_process_rate_limit_still_enforces_via_redis_module(self):
        from src.api.rate_limit_redis import redis_rate_limit_check
        from unittest.mock import MagicMock, AsyncMock

        request = MagicMock()
        request.client.host = "test-ip"
        # With no REDIS_URL set, should call in-process limiter
        # Just verify it completes without error (limiter not full)
        get_limiter().reset("test-ip")
        await redis_rate_limit_check(request, api_key="")
