"""API key authentication — reads API_KEYS env var (comma-separated).

If API_KEYS is unset or empty → auth disabled (dev mode).
If API_KEYS is set → X-Api-Key header is required and must match a listed key.
"""
import os
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status


def _valid_keys() -> frozenset[str]:
    raw = os.getenv("API_KEYS", "")
    if not raw.strip():
        return frozenset()
    return frozenset(k.strip() for k in raw.split(",") if k.strip())


async def verify_api_key(request: Request) -> str:
    """Return the validated key string, or raise HTTP 401.

    Returns empty string when auth is disabled (API_KEYS not set).
    """
    valid = _valid_keys()
    if not valid:
        return ""
    key = request.headers.get("X-Api-Key", "")
    if not key or key not in valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    return key


ApiKeyDep = Annotated[str, Depends(verify_api_key)]
