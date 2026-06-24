"""Integration tests for Phase 8 — auth and rate limiting via a minimal ASGI app.

Uses a lightweight FastAPI app (no database) so auth/rate-limit behaviour can be
verified end-to-end through the HTTP layer without spinning up PostgreSQL.
"""
from collections import deque
from time import monotonic

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from src.api.auth import verify_api_key
from src.api.rate_limit import get_limiter, rate_limit_check, _MAX_REQUESTS

# ── minimal ASGI app for testing ───────────────────────────────────────────────

_app = FastAPI()


@_app.get("/ping", dependencies=[Depends(rate_limit_check)])
async def ping() -> dict:
    return {"ok": True}


# ── fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def reset_limiter():
    get_limiter().reset()
    yield
    get_limiter().reset()


@pytest.fixture
def auth_client(monkeypatch):
    monkeypatch.setenv("API_KEYS", "sk-test")
    return TestClient(_app, raise_server_exceptions=True)


@pytest.fixture
def noauth_client(monkeypatch):
    monkeypatch.delenv("API_KEYS", raising=False)
    return TestClient(_app, raise_server_exceptions=True)


# ── auth tests ─────────────────────────────────────────────────────────────────

def test_missing_key_returns_401(auth_client):
    r = auth_client.get("/ping")
    assert r.status_code == 401


def test_invalid_key_returns_401(auth_client):
    r = auth_client.get("/ping", headers={"X-Api-Key": "sk-wrong"})
    assert r.status_code == 401


def test_valid_key_returns_200(auth_client):
    r = auth_client.get("/ping", headers={"X-Api-Key": "sk-test"})
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_auth_disabled_no_key_required(noauth_client):
    r = noauth_client.get("/ping")
    assert r.status_code == 200


def test_auth_disabled_any_key_accepted(noauth_client):
    r = noauth_client.get("/ping", headers={"X-Api-Key": "anything"})
    assert r.status_code == 200


# ── rate limit tests ───────────────────────────────────────────────────────────

def test_rate_limit_returns_429_when_bucket_full(auth_client):
    get_limiter()._buckets["sk-test"] = deque([monotonic()] * _MAX_REQUESTS)
    r = auth_client.get("/ping", headers={"X-Api-Key": "sk-test"})
    assert r.status_code == 429


def test_rate_limit_response_has_retry_after(auth_client):
    get_limiter()._buckets["sk-test"] = deque([monotonic()] * _MAX_REQUESTS)
    r = auth_client.get("/ping", headers={"X-Api-Key": "sk-test"})
    assert "retry-after" in r.headers
    assert int(r.headers["retry-after"]) >= 1


def test_rate_limit_detail_explains_retry(auth_client):
    get_limiter()._buckets["sk-test"] = deque([monotonic()] * _MAX_REQUESTS)
    r = auth_client.get("/ping", headers={"X-Api-Key": "sk-test"})
    assert "Retry" in r.json()["detail"]


def test_rate_limit_not_triggered_under_limit(auth_client):
    # Fill to MAX-1 then make one more — should pass
    get_limiter()._buckets["sk-test"] = deque([monotonic()] * (_MAX_REQUESTS - 1))
    r = auth_client.get("/ping", headers={"X-Api-Key": "sk-test"})
    assert r.status_code == 200


def test_rate_limit_separate_keys_independent(monkeypatch):
    monkeypatch.setenv("API_KEYS", "sk-a,sk-b")
    client = TestClient(_app, raise_server_exceptions=True)
    get_limiter()._buckets["sk-a"] = deque([monotonic()] * _MAX_REQUESTS)
    # sk-a is rate limited but sk-b must pass
    r_a = client.get("/ping", headers={"X-Api-Key": "sk-a"})
    r_b = client.get("/ping", headers={"X-Api-Key": "sk-b"})
    assert r_a.status_code == 429
    assert r_b.status_code == 200


def test_expired_requests_do_not_count(auth_client):
    from src.api.rate_limit import _WINDOW_SECONDS
    old = monotonic() - (_WINDOW_SECONDS + 1)
    get_limiter()._buckets["sk-test"] = deque([old] * _MAX_REQUESTS)
    # All requests are stale — new request should pass
    r = auth_client.get("/ping", headers={"X-Api-Key": "sk-test"})
    assert r.status_code == 200
