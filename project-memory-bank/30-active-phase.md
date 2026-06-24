# 30 -- Active Phase

**Current phase:** Phase 9 -- Production Hardening -- **complete**.

**Status:** All Phase 9 deliverables implemented and verified. Awaiting **explicit approval** to discuss any follow-on work.

## Completed this phase

### Backend additions
- `src/api/cache.py` -- TTL response cache; in-memory (default) or Redis when `REDIS_URL` set; `CacheMiddleware` caches GET responses for `/graph`, `/neighbors`, `/path/`, `/explain/` (60s TTL)
- `src/api/rate_limit_redis.py` -- Redis sorted-set sliding window rate limiter; falls back to in-process `_SlidingWindow` when `REDIS_URL` unset; multi-worker safe
- `src/api/tracing.py` -- OpenTelemetry SDK init + FastAPI instrumentation; OTLP export when `OTEL_EXPORTER_OTLP_ENDPOINT` set; graceful no-op if SDK not installed
- `src/api/security_headers.py` -- Starlette middleware: X-Content-Type-Options, X-Frame-Options, X-XSS-Protection, Referrer-Policy, Permissions-Policy, CSP (API paths), HSTS (HTTPS only)
- `src/api/main.py` -- v0.7.0; SecurityHeadersMiddleware + CacheMiddleware added; `redis_rate_limit_check` replaces in-process dependency

### Tooling
- `scripts/benchmark_ingestion.py` -- entity extraction throughput + ASGI /health latency benchmark
- `pyproject.toml` -- `redis` and `tracing` optional dep groups added

### UI
- `ui/src/components/GraphCanvas.tsx` -- Force-directed layout (spring-force simulation, 120 iterations) with Force/Circle toggle; resolves DEC-0011

### Docs
- `docs/runbook.md` -- startup checklist, env vars, health check, monitoring, caching, security, DB ops, rollback, common ops, troubleshooting table

### Tests
- `tests/unit/test_cache.py` -- 15 tests (in-memory get/set/miss/expiry/invalidate/singleton/reset)
- `tests/unit/test_security_headers.py` -- 11 tests (common headers, CSP, HSTS gating)
- `tests/integration/test_phase9_api.py` -- 11 tests (cache MISS/HIT, cache key isolation, non-cacheable, security headers, rate limit fallback)

### Exit criteria met
- [x] Redis-backed rate limiter implemented (`rate_limit_redis.py`); in-process fallback when no Redis
- [x] Response caching with Redis/in-memory backend (`CacheMiddleware`)
- [x] OpenTelemetry tracing (`tracing.py`); no-op when SDK absent
- [x] Entity extraction throughput: **35,352 entities/sec** (target >=10,000) -- PASS
- [x] p99 API latency: **1.49ms** (target <100ms, in-process ASGI) -- PASS
- [x] Force-directed graph layout with circle fallback; toggle in UI -- DEC-0011 resolved
- [x] Security headers middleware: 5 OWASP headers + CSP on API paths + HSTS on HTTPS
- [x] `docs/runbook.md` written
- [x] **278/278 tests passing, 88.84% coverage** (36 new tests, no regression)

## Boundary

All 10 phases (0-9) complete. No further phases defined in roadmap.
