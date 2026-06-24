"""Unit tests for API key authentication — src/api/auth.py."""
import os

import pytest
from fastapi import HTTPException
from unittest.mock import MagicMock

from src.api.auth import verify_api_key


def _request(api_key: str | None = None) -> MagicMock:
    req = MagicMock()
    req.headers = {"X-Api-Key": api_key} if api_key is not None else {}
    return req


# ── auth disabled (API_KEYS not set) ──────────────────────────────────────────

class TestAuthDisabled:
    def setup_method(self):
        os.environ.pop("API_KEYS", None)

    async def test_no_key_passes(self):
        result = await verify_api_key(_request())
        assert result == ""

    async def test_any_key_value_passes(self):
        result = await verify_api_key(_request("random-key"))
        assert result == ""  # auth disabled — returns empty string, not the supplied key

    async def test_empty_api_keys_env_disables_auth(self, monkeypatch):
        monkeypatch.setenv("API_KEYS", "")
        result = await verify_api_key(_request())
        assert result == ""

    async def test_whitespace_api_keys_disables_auth(self, monkeypatch):
        monkeypatch.setenv("API_KEYS", "   ")
        result = await verify_api_key(_request())
        assert result == ""


# ── auth enabled (API_KEYS set) ───────────────────────────────────────────────

class TestAuthEnabled:
    def setup_method(self):
        os.environ["API_KEYS"] = "sk-valid,sk-other"

    def teardown_method(self):
        os.environ.pop("API_KEYS", None)

    async def test_missing_key_raises_401(self):
        with pytest.raises(HTTPException) as exc:
            await verify_api_key(_request())
        assert exc.value.status_code == 401

    async def test_invalid_key_raises_401(self):
        with pytest.raises(HTTPException) as exc:
            await verify_api_key(_request("sk-invalid"))
        assert exc.value.status_code == 401

    async def test_valid_key_returns_key(self):
        result = await verify_api_key(_request("sk-valid"))
        assert result == "sk-valid"

    async def test_second_listed_key_passes(self):
        result = await verify_api_key(_request("sk-other"))
        assert result == "sk-other"

    async def test_401_includes_www_authenticate(self):
        with pytest.raises(HTTPException) as exc:
            await verify_api_key(_request("bad"))
        assert exc.value.headers is not None
        assert "WWW-Authenticate" in exc.value.headers

    async def test_keys_with_whitespace_are_stripped(self, monkeypatch):
        monkeypatch.setenv("API_KEYS", "  sk-spaced  ,  sk-other  ")
        result = await verify_api_key(_request("sk-spaced"))
        assert result == "sk-spaced"

    async def test_empty_key_header_raises_401(self):
        with pytest.raises(HTTPException) as exc:
            await verify_api_key(_request(""))
        assert exc.value.status_code == 401
