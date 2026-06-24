# 33 — Next Actions

Phase 7 is complete. Awaiting approval for Phase 8.

## On approval: begin Phase 8 — Public Platform

Phase 8 exposes the Knowledge Graph Layer as a production-grade public API with
an OpenAPI spec, a typed SDK, and developer documentation.

### Phase 8 deliverables

1. **OpenAPI spec** — auto-generated via FastAPI + manually enriched with examples, descriptions, and error schemas; exported as `docs/openapi.json`
2. **Typed Python SDK** — `sdk/` directory: `KnowledgeGraphClient` class wrapping all endpoints; `pip install -e .` installable; full type hints
3. **API key auth** — `X-Api-Key` header middleware; keys stored in config/env; 401 on invalid key
4. **Rate limiting** — in-process sliding window (100 req/min per key); 429 response on exceed
5. **Developer docs** — `docs/api-guide.md`: authentication, rate limits, quickstart examples, endpoint reference
6. **Sample integration** — `examples/ingest_and_query.py`: end-to-end demo (ingest records → query graph → explain entity)

### Phase 8 exit criteria
- `GET /v1/openapi.json` returns full OpenAPI 3.1 spec
- SDK `KnowledgeGraphClient` covers all v1 endpoints; passes `mypy --strict`
- Invalid API key returns 401; missing key returns 401
- 101st request within 60s returns 429
- Developer guide readable in browser (Markdown render)
- Sample integration runs against a live server end-to-end

_Do not proceed without explicit user approval (phase-execution model)._
