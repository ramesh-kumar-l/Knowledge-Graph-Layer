# 30 — Active Phase

**Current phase:** Phase 8 — Public Platform → **complete**.

**Status:** Auth, rate limiting, SDK, developer docs, and sample integration all implemented. Awaiting **explicit approval** to begin Phase 9.

## Completed this phase

### Backend additions
- `src/api/auth.py` — `verify_api_key` dependency; `API_KEYS` env var; dev-mode bypass when unset
- `src/api/rate_limit.py` — `_SlidingWindow` (100 req/60s per key); `rate_limit_check` dependency (chains auth → limit)
- `src/api/main.py` — `_v1_deps = [Depends(rate_limit_check)]` applied to all 7 v1 routers; `/v1/openapi.json` alias; version 0.6.0; OpenAPI tags + enriched description

### SDK (`sdk/`)
- `sdk/pyproject.toml` — `scp-knowledge-graph-sdk 0.6.0`; deps: httpx, pydantic; `pip install -e sdk/`
- `sdk/knowledge_graph/models.py` — Pydantic models matching all API types (Entity, Relationship, TrustScore, GraphResponse, PathResponse, ExplainResponse, MemoryRecord, commands, enums)
- `sdk/knowledge_graph/client.py` — `KnowledgeGraphClient` async client; all 17 v1 endpoints; typed return types; `KnowledgeGraphError`
- `sdk/knowledge_graph/__init__.py` — public exports

### Docs + tooling
- `docs/api-guide.md` — authentication, rate limiting, quickstart (SDK + cURL), full endpoint reference table
- `docs/openapi.json` — OpenAPI 3.1.0 spec (21 paths); auto-exported via `scripts/export_openapi.py`
- `scripts/export_openapi.py` — one-shot export script
- `examples/ingest_and_query.py` — end-to-end demo: ingest 2 records → list entities → graph query → trust explanation → conflict queue

### Tests
- `tests/unit/test_auth.py` — 11 tests (disabled/enabled modes, 401 variants, whitespace handling)
- `tests/unit/test_rate_limit.py` — 12 tests (allow/deny, key isolation, window expiry, reset)
- `tests/integration/test_phase8_api.py` — 11 tests via lightweight ASGI app (HTTP-level auth + rate limit)

### Exit criteria met
- [x] `GET /v1/openapi.json` returns OpenAPI 3.1.0 spec (21 paths, version 0.6.0)
- [x] SDK `KnowledgeGraphClient` covers all v1 endpoints; Pydantic models are fully typed
- [x] Invalid API key returns 401; missing key returns 401 (when `API_KEYS` is set)
- [x] Auth disabled when `API_KEYS` env var is unset (dev mode)
- [x] Bucket-full request returns 429 with `Retry-After` header
- [x] Developer guide in `docs/api-guide.md`
- [x] Sample integration in `examples/ingest_and_query.py`
- [x] `scripts/export_openapi.py` exports spec successfully
- [x] **242/242 Python tests passing, 90.38% coverage** (34 new, no regression)

## Known limitations
- Rate limiter is in-process only — multiple gunicorn workers share nothing (Redis-backed for Phase 9)
- SDK is not published to PyPI (pip install -e sdk/ for local use)
- `mypy --strict` on SDK requires httpx and pydantic stubs installed in SDK environment

## Boundary
- Do NOT begin Phase 9 (Production Hardening) until the user approves.

## Next phase
Phase 9 — Production Hardening. See `33-next-actions.md`.
