# SCP Knowledge Graph Layer — Production Runbook

## Quick reference

| Action | Command |
|--------|---------|
| Start API server | `uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --workers 4` |
| Health check | `curl http://localhost:8000/health` |
| Run migrations | `alembic upgrade head` |
| Export OpenAPI spec | `python scripts/export_openapi.py` |
| Run benchmarks | `python scripts/benchmark_ingestion.py` |
| Run tests | `pytest --cov=src` |

---

## Environment variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | — | PostgreSQL URL: `postgresql+asyncpg://user:pass@host/db` |
| `API_KEYS` | No | (auth disabled) | Comma-separated API keys: `sk-prod1,sk-prod2` |
| `REDIS_URL` | No | (in-process) | Redis URL: `redis://localhost:6379/0`. Enables shared rate limiting and response caching. |
| `CORS_ORIGINS` | No | `http://localhost:5173` | Comma-separated allowed origins |
| `OTEL_SERVICE_NAME` | No | `scp-knowledge-graph` | Service name in traces |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | No | (no export) | OTLP collector URL: `http://localhost:4318` |

---

## Startup checklist

1. **Database** — verify PostgreSQL is reachable and migrations are current:
   ```bash
   alembic current        # should show: head
   alembic upgrade head   # run migrations if behind
   ```

2. **API keys** — set `API_KEYS` to a comma-separated list of secret keys. If omitted, auth is disabled (dev mode only).

3. **Redis** (recommended for multi-worker) — set `REDIS_URL`. Without Redis, each worker maintains an independent in-process rate limiter and cache, which is unsafe in multi-process deployments.

4. **Start server**:
   ```bash
   uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --workers 4
   ```

5. **Confirm health**:
   ```bash
   curl http://localhost:8000/health
   # Expected: {"status":"ok","version":"0.7.0"}
   ```

---

## Health check

`GET /health` — returns 200 when the process is running. Does not check DB connectivity.

For a deeper readiness check, query an entity list:
```bash
curl -H "X-Api-Key: $API_KEY" http://localhost:8000/v1/entities?limit=1
```

Expected: 200 with `{"items":[],"total":0}` on an empty database.

---

## Monitoring

### Key metrics to watch

| Metric | Warning | Critical |
|--------|---------|----------|
| HTTP error rate (5xx) | > 1% | > 5% |
| p99 API latency | > 100ms | > 500ms |
| 429 rate (rate limit hits) | > 5% of traffic | > 20% |
| DB connection pool saturation | > 80% | > 95% |
| Redis memory usage | > 80% maxmemory | > 95% |

### OpenTelemetry

When `OTEL_EXPORTER_OTLP_ENDPOINT` is set and the OTel SDK is installed:
```bash
pip install opentelemetry-sdk opentelemetry-instrumentation-fastapi opentelemetry-exporter-otlp-proto-http
```

Traces are exported to the configured collector (Jaeger, Tempo, etc.). All FastAPI
routes are instrumented automatically. Service name is set by `OTEL_SERVICE_NAME`.

### Rate limit monitoring

Rate limit responses return HTTP 429 with `Retry-After` header. Track 429 counts
by API key (`X-Api-Key` request header) to identify abusive clients.

---

## Response caching

Graph traversal (`/graph`, `/neighbors`, `/path/`) and trust explanation (`/explain/`)
responses are cached for 60 seconds. Cache hit/miss is visible in the `X-Cache` header.

- **HIT**: served from cache, zero DB I/O.
- **MISS**: computed fresh, result stored in cache.

Cache keys include the full request path and query string, so different parameter
combinations get independent cache entries.

With `REDIS_URL` set, cache is shared across all workers. Without it, each worker
has an independent in-process cache.

To force a cache refresh, add any unique query param (e.g., `?_t=<timestamp>`).

---

## Security

### API key management

Keys are read from the `API_KEYS` environment variable at startup. To rotate a key:
1. Add the new key to `API_KEYS` (keep the old key alongside it).
2. Restart the server (picks up the env var change).
3. Migrate clients to the new key.
4. Remove the old key from `API_KEYS`.
5. Restart the server again.

### Rate limiting

Default: 100 requests per 60 seconds per API key. Exceeded requests receive HTTP 429
with `Retry-After: 60`.

To adjust limits, change `_WINDOW` and `_MAX` constants in `src/api/rate_limit_redis.py`
and restart.

### Security headers

All responses include:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Content-Security-Policy: default-src 'none'; ...` (API endpoints only)
- `Strict-Transport-Security: max-age=63072000; ...` (HTTPS only)

---

## Database operations

### Running migrations

```bash
alembic upgrade head    # apply all pending migrations
alembic downgrade -1    # roll back one migration
alembic history         # show migration history
```

### Backup (PostgreSQL)

```bash
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d_%H%M%S).sql
```

---

## Rollback procedure

1. **Identify the bad deploy** — check `/health` and recent error logs.
2. **Stop the server** — `kill -SIGTERM <uvicorn-pid>` (graceful) or `kill -9` (force).
3. **Roll back code** — `git checkout <previous-tag>`.
4. **Roll back migration** (if schema changed) — `alembic downgrade -1`.
5. **Restart server** with previous version.
6. **Verify health** — `curl http://localhost:8000/health`.

---

## Common operations

### Inspect conflict queue

```bash
curl -H "X-Api-Key: $API_KEY" http://localhost:8000/v1/conflict/queue
```

### Resolve a conflict

```bash
curl -X POST -H "X-Api-Key: $API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"resolution": "VERIFIED", "resolved_by": "operator"}' \
     http://localhost:8000/v1/conflict/<conflict-id>/resolve
```

### Export OpenAPI spec

```bash
python scripts/export_openapi.py
# writes to docs/openapi.json
```

### Run performance benchmark

```bash
python scripts/benchmark_ingestion.py
# reports entity extraction throughput and API latency percentiles
```

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| 401 on all requests | `API_KEYS` set but wrong key | Check `API_KEYS` env var; use correct `X-Api-Key` header |
| 429 on first request | Clock skew in Redis window | Check Redis time vs server time; restart Redis client |
| Slow queries | Cache miss + large graph | Check `X-Cache` header; verify Redis is connected |
| High 5xx rate | DB unavailable | Check `DATABASE_URL`, PostgreSQL status, connection pool |
| Missing traces | OTel not configured | Check `OTEL_EXPORTER_OTLP_ENDPOINT`; `pip install opentelemetry-sdk` |
| Workers desynchronized | No Redis for shared state | Set `REDIS_URL` for multi-worker deployments |
