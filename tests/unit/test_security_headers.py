"""Unit tests for src/api/security_headers.py."""
import pytest
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport

from src.api.security_headers import SecurityHeadersMiddleware, _COMMON_HEADERS, _CSP


def _make_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)

    @app.get("/ping")
    async def ping():
        return {"ok": True}

    @app.get("/docs-path")
    async def docs_path():
        return {"ok": True}

    return app


@pytest.fixture
def app():
    return _make_app()


class TestCommonHeaders:
    async def test_x_content_type_options(self, app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/ping")
        assert resp.headers["x-content-type-options"] == "nosniff"

    async def test_x_frame_options(self, app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/ping")
        assert resp.headers["x-frame-options"] == "DENY"

    async def test_x_xss_protection(self, app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/ping")
        assert resp.headers["x-xss-protection"] == "1; mode=block"

    async def test_referrer_policy(self, app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/ping")
        assert resp.headers["referrer-policy"] == "strict-origin-when-cross-origin"

    async def test_permissions_policy(self, app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/ping")
        assert "permissions-policy" in resp.headers


class TestCSP:
    async def test_csp_on_api_endpoint(self, app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/ping")
        assert "content-security-policy" in resp.headers
        assert "default-src 'none'" in resp.headers["content-security-policy"]

    async def test_no_csp_on_docs_paths(self, app):
        # /docs is excluded from CSP (Swagger UI loads CDN assets)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/docs")
        # /docs returns 404 in our minimal app but headers are still added
        assert "content-security-policy" not in resp.headers or "/docs" not in resp.url.path


class TestHSTS:
    async def test_no_hsts_over_http(self, app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/ping")
        assert "strict-transport-security" not in resp.headers

    async def test_all_common_headers_present(self, app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/ping")
        for header in _COMMON_HEADERS:
            assert header.lower() in resp.headers, f"Missing header: {header}"
