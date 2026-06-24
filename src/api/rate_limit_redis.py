"""Redis sliding-window rate limiter — multi-worker safe replacement for rate_limit.py.

When REDIS_URL is set: uses sorted sets (ZREMRANGEBYSCORE + ZADD + ZCARD pipeline).
When REDIS_URL is unset: delegates to the in-process _SlidingWindow fallback.
"""
import os
import uuid
from time import time
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

from src.api.auth import verify_api_key
from src.api.rate_limit import get_limiter

_REDIS_URL = os.getenv("REDIS_URL", "")
_WINDOW: int = 60
_MAX: int = 100
_PREFIX = "kg:rl:"

_redis_client = None


async def _get_redis():
    global _redis_client
    if _redis_client is None and _REDIS_URL:
        import redis.asyncio as aioredis  # type: ignore[import]
        _redis_client = aioredis.from_url(_REDIS_URL, decode_responses=True)
    return _redis_client


async def _check_redis(bucket: str) -> None:
    client = await _get_redis()
    if client is None:
        return
    rkey = f"{_PREFIX}{bucket}"
    now = time()
    window_start = now - _WINDOW
    member = f"{now}:{uuid.uuid4().hex}"

    async with client.pipeline(transaction=True) as pipe:
        pipe.zremrangebyscore(rkey, "-inf", window_start)
        pipe.zadd(rkey, {member: now})
        pipe.zcard(rkey)
        pipe.expire(rkey, _WINDOW + 10)
        results = await pipe.execute()
    count = results[2]

    if count > _MAX:
        await client.zrem(rkey, member)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Retry in {_WINDOW}s.",
            headers={"Retry-After": str(_WINDOW)},
        )


async def redis_rate_limit_check(
    request: Request,
    api_key: str = Depends(verify_api_key),
) -> None:
    """Redis rate limit when REDIS_URL is set; in-process fallback otherwise."""
    bucket = api_key or (request.client.host if request.client else "unknown")
    if _REDIS_URL:
        await _check_redis(bucket)
    else:
        await get_limiter().check(bucket)


RedisRateLimitDep = Annotated[None, Depends(redis_rate_limit_check)]
