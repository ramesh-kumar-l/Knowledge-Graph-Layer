"""In-process sliding window rate limiter — 100 req/60s per API key (or IP in dev mode).

Single-process; for multi-process deployments (gunicorn), replace with Redis.
"""
from collections import deque
from time import monotonic
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

from src.api.auth import verify_api_key

_WINDOW_SECONDS: float = 60.0
_MAX_REQUESTS: int = 100


class _SlidingWindow:
    def __init__(self) -> None:
        self._buckets: dict[str, deque[float]] = {}

    async def check(self, key: str) -> None:
        now = monotonic()
        cutoff = now - _WINDOW_SECONDS
        bucket = self._buckets.setdefault(key, deque())
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
        if len(bucket) >= _MAX_REQUESTS:
            retry_after = max(1, int(_WINDOW_SECONDS - (now - bucket[0])) + 1)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Retry in {retry_after}s.",
                headers={"Retry-After": str(retry_after)},
            )
        bucket.append(now)

    def reset(self, key: str | None = None) -> None:
        if key is not None:
            self._buckets.pop(key, None)
        else:
            self._buckets.clear()


_limiter = _SlidingWindow()


async def rate_limit_check(
    request: Request,
    api_key: str = Depends(verify_api_key),
) -> None:
    """Enforce rate limit; chains through verify_api_key so auth runs first."""
    bucket_key = api_key or (request.client.host if request.client else "unknown")
    await _limiter.check(bucket_key)


def get_limiter() -> _SlidingWindow:
    return _limiter


RateLimitDep = Annotated[None, Depends(rate_limit_check)]
