# 90 — Session Handoff

**Session date:** 2026-06-24
**Phases completed:** Phase 0 through Phase 8

---

## Phase 8 Summary — Public Platform

### Backend changes

**`src/api/auth.py`** (new):
- `verify_api_key(request)` → reads `API_KEYS` env var (comma-separated keys)
- If `API_KEYS` is empty/unset → returns `""` (auth disabled, dev mode)
- If set → validates `X-Api-Key` header; raises 401 on missing/invalid key
- `ApiKeyDep = Annotated[str, Depends(verify_api_key)]`

**`src/api/rate_limit.py`** (new):
- `_SlidingWindow`: dict of deques, one per bucket key; prunes expired entries on each check
- Window: 100 req / 60s; raises 429 with `Retry-After` header when exceeded
- `rate_limit_check(request, api_key=Depends(verify_api_key))`: uses `api_key` as bucket (falls back to IP in dev mode)
- `get_limiter()`: returns module-level singleton (for tests to reset)

**`src/api/main.py`** (updated):
- `_v1_deps = [Depends(rate_limit_check)]` added to all 7 `app.include_router(...)` calls
- `/v1/openapi.json` alias route added (public, returns `app.openapi()`)
- Version: 0.5.0 → 0.6.0
- OpenAPI tags + enriched description added

### SDK (`sdk/`)

```
sdk/
  pyproject.toml                   (scp-knowledge-graph-sdk 0.6.0; httpx+pydantic)
  knowledge_graph/
    __init__.py                    (exports KnowledgeGraphClient, all models)
    models.py                      (Pydantic mirrors of all API types, ~250 lines)
    client.py                      (KnowledgeGraphClient async httpx client, ~230 lines)
```

`KnowledgeGraphClient` covers: list/get/create/update/delete entities, entity versions, create relationships, list relationships, ingest memory records, graph traversal (graph/neighbors/path), explain entity, get dispute queue, resolve conflict.

Install: `pip install -e sdk/`

### Developer docs + tooling

- `docs/api-guide.md` — auth, rate limits, SDK quickstart, cURL examples, endpoint reference table, running locally
- `docs/openapi.json` — OpenAPI 3.1.0 spec (21 paths); regenerate: `python scripts/export_openapi.py`
- `scripts/export_openapi.py` — imports `src.api.main.app`, calls `app.openapi()`, writes to `docs/openapi.json`
- `examples/ingest_and_query.py` — end-to-end demo (ingest → list → graph → explain → conflicts)

### Tests
- `tests/unit/test_auth.py` — 11 tests
- `tests/unit/test_rate_limit.py` — 12 tests
- `tests/integration/test_phase8_api.py` — 11 tests (lightweight ASGI app, no DB)
- **242/242 tests, 90.38% coverage**

---

## Dev server startup

```bash
# Terminal 1 — backend (set API_KEYS for auth enforcement)
cd E:\ClaudeProjects\Knowledge-Graph-Layer
set API_KEYS=sk-dev
uvicorn src.api.main:app --reload --port 8000

# Terminal 2 — UI
cd E:\ClaudeProjects\Knowledge-Graph-Layer\ui
npm run dev
# http://localhost:5173

# Export OpenAPI spec
python scripts/export_openapi.py

# Run sample integration
python examples/ingest_and_query.py
```

---

## Known limitations / Phase 9 notes
- Rate limiter is in-process; no shared state across gunicorn workers → Redis limiter in Phase 9
- SDK not published to PyPI
- No force-directed graph layout (deferred since DEC-0011, Phase 9 enhancement)
- No distributed tracing / OpenTelemetry yet
- No Redis caching layer yet

## STOP
Phase 8 complete. Awaiting explicit user approval before Phase 9 (Production Hardening).
