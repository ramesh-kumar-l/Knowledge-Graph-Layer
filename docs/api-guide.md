# SCP Knowledge Graph Layer — API Developer Guide

**Version:** 0.6.0 | **Base URL:** `http://localhost:8000`

---

## Authentication

All `/v1/*` endpoints require an API key in the `X-Api-Key` header.

```
X-Api-Key: sk-your-key-here
```

Keys are configured server-side via the `API_KEYS` environment variable (comma-separated):

```bash
export API_KEYS="sk-prod-key1,sk-prod-key2"
uvicorn src.api.main:app --port 8000
```

**Development mode:** If `API_KEYS` is not set, authentication is disabled. All requests pass through without a key. Suitable for local development only.

**Error responses:**
- `401 Unauthorized` — missing or invalid `X-Api-Key`

---

## Rate Limiting

**Limit:** 100 requests per 60 seconds, per API key.

When the limit is exceeded:

```
HTTP/1.1 429 Too Many Requests
Retry-After: 42

{"detail": "Rate limit exceeded. Retry in 42s."}
```

In production with multiple workers, rate limits are per-process. Deploy a Redis-backed limiter for distributed enforcement (Phase 9).

---

## Quickstart

### Python SDK (recommended)

```bash
cd sdk && pip install -e .
```

```python
import asyncio
from knowledge_graph import KnowledgeGraphClient, MemoryRecord

async def main():
    async with KnowledgeGraphClient("http://localhost:8000", api_key="sk-dev") as client:
        # Ingest a memory record
        await client.ingest_memory_record(MemoryRecord(
            content="Alice manages the platform team at Acme Corp.",
            source="slack",
        ))

        # Query the knowledge graph
        entities = await client.list_entities(limit=10)
        for e in entities:
            print(e.name, e.type, e.confidence)

asyncio.run(main())
```

### cURL

```bash
# List entities
curl -H "X-Api-Key: sk-dev" http://localhost:8000/v1/entities/

# Ingest a memory record
curl -X POST http://localhost:8000/v1/ingest/memory-record \
  -H "X-Api-Key: sk-dev" \
  -H "Content-Type: application/json" \
  -d '{"content": "Alice works at Acme Corp.", "source": "slack"}'

# Get entity graph (replace UUID)
curl -H "X-Api-Key: sk-dev" \
  "http://localhost:8000/v1/entities/<uuid>/graph?max_depth=2&min_confidence=0.5"

# Explain trust score
curl -H "X-Api-Key: sk-dev" http://localhost:8000/v1/explain/<uuid>
```

---

## Endpoint Reference

### Ingestion

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/v1/ingest/memory-record` | Extract entities and relationships from a raw memory record |

**Request body:**
```json
{
  "content": "Alice is the CTO of Acme Corp.",
  "source": "email",
  "author": "system",
  "tags": ["people"],
  "attributes": {}
}
```

---

### Entities

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/v1/entities/` | List active entities (`?limit=100&search=alice`) |
| `GET` | `/v1/entities/{id}` | Get entity by ID |
| `POST` | `/v1/entities/` | Create entity |
| `PATCH` | `/v1/entities/{id}` | Update entity fields |
| `DELETE` | `/v1/entities/{id}` | Soft-delete entity |
| `GET` | `/v1/entities/{id}/versions` | Full version history |

---

### Graph Queries

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/v1/entities/{id}/graph` | BFS traversal from entity |
| `GET` | `/v1/entities/{id}/neighbors` | Immediate neighbors (depth 1) |
| `GET` | `/v1/entities/{from}/path/{to}` | Shortest path between two entities |

**Query parameters:**
- `max_depth` — traversal depth (1–5, default 3)
- `direction` — `OUTBOUND`, `INBOUND`, or `BOTH` (default)
- `min_confidence` — filter edges below threshold (0.0–1.0)
- `limit` — max nodes returned (1–500)

---

### Relationships

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/v1/relationships/` | List relationships |
| `POST` | `/v1/relationships/` | Create relationship |

---

### Trust & Explanation

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/v1/explain/{id}` | Full trust breakdown: score, evidence, provenance, conflict history |

**Response includes:**
- `trust_score.overall_confidence` — 0.0–1.0
- `trust_score.components.evidence_weight` — weighted by source count
- `trust_score.components.freshness_decay` — time-decayed
- `trust_score.components.verification_bonus` — VERIFIED state adds 0.1
- `trust_score.components.conflict_penalty` — DISPUTED state subtracts 0.15

---

### Conflict Resolution

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/v1/conflict/queue` | All DISPUTED entities |
| `POST` | `/v1/conflict/{id}/resolve` | Accept (→VERIFIED) or reject (→UNVERIFIED) |

**Request body:**
```json
{
  "decision": "ACCEPT",
  "resolved_by": "analyst@example.com",
  "reason": "Verified via primary source"
}
```

---

### System

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check (no auth required) |
| `GET` | `/v1/openapi.json` | OpenAPI 3.1 spec (no auth required) |
| `GET` | `/docs` | Interactive Swagger UI |
| `GET` | `/redoc` | ReDoc documentation |

---

## OpenAPI Spec

Export the spec to `docs/openapi.json`:

```bash
python scripts/export_openapi.py
```

The spec is also served live at `http://localhost:8000/v1/openapi.json`.

---

## Running Locally

```bash
# Terminal 1 — Backend
export API_KEYS="sk-dev"          # optional in dev
uvicorn src.api.main:app --reload --port 8000

# Terminal 2 — UI (Knowledge Explorer)
cd ui && npm run dev               # http://localhost:5173

# Terminal 3 — Run the example
python examples/ingest_and_query.py
```

---

## Verification States

| State | Meaning |
|-------|---------|
| `UNVERIFIED` | Extracted but not validated |
| `VERIFIED` | Confirmed by a human or trusted source |
| `DISPUTED` | Conflicting evidence detected |
| `RETRACTED` | Previously accepted, now withdrawn |
