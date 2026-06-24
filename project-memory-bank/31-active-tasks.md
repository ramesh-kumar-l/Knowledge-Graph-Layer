# 31 -- Active Tasks

## Done

### Phase 0-8 (see session-handoff for details)
- [x] All phases 0-8 complete. 242 tests, 90.38% coverage. Public API + SDK.

### Phase 9 -- Production Hardening
- [x] `src/api/cache.py` -- TTL cache (in-memory + Redis backend); CacheMiddleware
- [x] `src/api/rate_limit_redis.py` -- Redis sliding window rate limiter; in-process fallback
- [x] `src/api/tracing.py` -- OpenTelemetry SDK init; OTLP export; FastAPI instrumentation
- [x] `src/api/security_headers.py` -- OWASP security headers middleware
- [x] `src/api/main.py` -- v0.7.0; all three new middleware wired in
- [x] `pyproject.toml` -- redis + tracing optional dep groups
- [x] `scripts/benchmark_ingestion.py` -- entity/sec + p99 latency benchmark
- [x] `ui/src/components/GraphCanvas.tsx` -- force-directed layout; Force/Circle toggle
- [x] `docs/runbook.md` -- production runbook
- [x] `tests/unit/test_cache.py` -- 15 tests
- [x] `tests/unit/test_security_headers.py` -- 11 tests
- [x] `tests/integration/test_phase9_api.py` -- 11 tests (cache + security headers + rate limit)
- [x] 278/278 tests pass, 88.84% coverage

## Pending

No pending tasks. All 10 phases (0-9) complete.
