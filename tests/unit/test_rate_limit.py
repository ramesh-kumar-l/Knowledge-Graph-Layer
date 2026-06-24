"""Unit tests for in-process sliding window rate limiter — src/api/rate_limit.py."""
from collections import deque
from time import monotonic

import pytest
from fastapi import HTTPException

from src.api.rate_limit import _SlidingWindow, _MAX_REQUESTS, _WINDOW_SECONDS


# ── helpers ────────────────────────────────────────────────────────────────────

def _limiter() -> _SlidingWindow:
    """Fresh limiter for each test."""
    return _SlidingWindow()


# ── basic allow/deny ───────────────────────────────────────────────────────────

async def test_requests_under_limit_pass():
    lim = _limiter()
    for _ in range(_MAX_REQUESTS - 1):
        await lim.check("key")


async def test_exactly_at_limit_passes():
    lim = _limiter()
    for _ in range(_MAX_REQUESTS):
        await lim.check("key")


async def test_one_over_limit_raises_429():
    lim = _limiter()
    for _ in range(_MAX_REQUESTS):
        await lim.check("key")
    with pytest.raises(HTTPException) as exc:
        await lim.check("key")
    assert exc.value.status_code == 429


async def test_429_response_has_retry_after_header():
    lim = _limiter()
    lim._buckets["k"] = deque([monotonic()] * _MAX_REQUESTS)
    with pytest.raises(HTTPException) as exc:
        await lim.check("k")
    assert "Retry-After" in exc.value.headers
    assert int(exc.value.headers["Retry-After"]) >= 1


async def test_detail_message_mentions_retry():
    lim = _limiter()
    lim._buckets["k"] = deque([monotonic()] * _MAX_REQUESTS)
    with pytest.raises(HTTPException) as exc:
        await lim.check("k")
    assert "Retry" in exc.value.detail


# ── key isolation ──────────────────────────────────────────────────────────────

async def test_different_keys_are_independent():
    lim = _limiter()
    for _ in range(_MAX_REQUESTS):
        await lim.check("keyA")
    # keyB is in a separate bucket — should not be rate limited
    await lim.check("keyB")


async def test_filled_key_does_not_affect_another():
    lim = _limiter()
    lim._buckets["full"] = deque([monotonic()] * _MAX_REQUESTS)
    await lim.check("empty")  # different key — must pass


# ── sliding window expiry ──────────────────────────────────────────────────────

async def test_old_requests_expire_from_window():
    lim = _limiter()
    old = monotonic() - (_WINDOW_SECONDS + 1)
    lim._buckets["key"] = deque([old] * _MAX_REQUESTS)
    # All old — window is clear, new request should pass
    await lim.check("key")


async def test_mixed_old_and_new_counts_correctly():
    lim = _limiter()
    old = monotonic() - (_WINDOW_SECONDS + 1)
    # 50 old + 50 new = 50 in window (under limit)
    lim._buckets["key"] = deque([old] * 50 + [monotonic()] * 50)
    await lim.check("key")  # 51st new request — still under limit of 100


# ── reset ──────────────────────────────────────────────────────────────────────

async def test_reset_specific_key():
    lim = _limiter()
    lim._buckets["k"] = deque([monotonic()] * _MAX_REQUESTS)
    lim.reset("k")
    await lim.check("k")  # bucket cleared — should pass


async def test_reset_all_keys():
    lim = _limiter()
    lim._buckets["a"] = deque([monotonic()] * _MAX_REQUESTS)
    lim._buckets["b"] = deque([monotonic()] * _MAX_REQUESTS)
    lim.reset()
    await lim.check("a")
    await lim.check("b")


async def test_reset_nonexistent_key_is_safe():
    lim = _limiter()
    lim.reset("ghost")  # should not raise
