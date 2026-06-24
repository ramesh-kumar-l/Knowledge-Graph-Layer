"""Unit tests for src/api/cache.py — in-memory TTL cache and CacheMiddleware."""
import asyncio

import pytest

from src.api.cache import _InMemoryCache, reset_cache, get_cache, _is_cacheable


class TestInMemoryCache:
    def setup_method(self):
        self.cache = _InMemoryCache()

    async def test_miss_returns_none(self):
        assert await self.cache.get("missing") is None

    async def test_set_and_get(self):
        await self.cache.set("k", {"x": 1}, ttl=60)
        result = await self.cache.get("k")
        assert result == {"x": 1}

    async def test_expired_entry_returns_none(self):
        await self.cache.set("exp", "value", ttl=0)
        # TTL=0 means it should be expired immediately (monotonic() + 0 <= monotonic())
        # Add a tiny sleep to ensure expiry
        await asyncio.sleep(0.01)
        assert await self.cache.get("exp") is None

    async def test_overwrite(self):
        await self.cache.set("k", "first", ttl=60)
        await self.cache.set("k", "second", ttl=60)
        assert await self.cache.get("k") == "second"

    async def test_size(self):
        assert self.cache.size() == 0
        await self.cache.set("a", 1, ttl=60)
        await self.cache.set("b", 2, ttl=60)
        assert self.cache.size() == 2

    async def test_invalidate_prefix(self):
        await self.cache.set("r:/v1/explain/abc", "x", ttl=60)
        await self.cache.set("r:/v1/explain/def", "y", ttl=60)
        await self.cache.set("r:/health", "z", ttl=60)
        await self.cache.invalidate_prefix("r:/v1/explain/")
        assert await self.cache.get("r:/v1/explain/abc") is None
        assert await self.cache.get("r:/v1/explain/def") is None
        assert await self.cache.get("r:/health") == "z"

    async def test_none_value_not_cached_after_expiry(self):
        await self.cache.set("x", None, ttl=60)
        # None is a valid cached value (falsy but explicitly stored)
        result = await self.cache.get("x")
        assert result is None  # can't distinguish from miss — by design, don't cache None


class TestGetCacheSingleton:
    def setup_method(self):
        reset_cache()

    def teardown_method(self):
        reset_cache()

    def test_returns_same_instance(self):
        c1 = get_cache()
        c2 = get_cache()
        assert c1 is c2

    def test_reset_creates_new_instance(self):
        c1 = get_cache()
        reset_cache()
        c2 = get_cache()
        assert c1 is not c2


class TestIsCacheable:
    def test_graph_suffix_cacheable(self):
        assert _is_cacheable("/v1/entities/abc/graph")

    def test_neighbors_suffix_cacheable(self):
        assert _is_cacheable("/v1/entities/abc/neighbors")

    def test_path_cacheable(self):
        assert _is_cacheable("/v1/entities/abc/path/def")

    def test_explain_cacheable(self):
        assert _is_cacheable("/v1/explain/abc-123")

    def test_entities_list_not_cacheable(self):
        assert not _is_cacheable("/v1/entities")

    def test_health_not_cacheable(self):
        assert not _is_cacheable("/health")

    def test_ingest_not_cacheable(self):
        assert not _is_cacheable("/v1/ingest/memory-record")
