# 04 — Roadmap

Execute exactly one phase at a time. Stop after each phase for explicit approval.

| Phase | Name                  | Deliverables (summary)                                                        |
|-------|-----------------------|-------------------------------------------------------------------------------|
| 0     | Bootstrap             | project-memory-bank structure + foundational direction. **(current)**         |
| 1     | Domain Model          | Domain model, entity/relationship taxonomy, evidence & provenance models, graph schema, ADRs. Docs only. |
| 2     | Storage Foundation    | Persistence schema, repositories, CRUD APIs, versioning, migration strategy, unit tests. |
| 3     | Entity Engine         | Entity extraction, normalization, deduplication, confidence scoring, validation. |
| 4     | Relationship Engine   | Relationship extraction/discovery, evidence linking, validation, trust integration. |
| 5     | Query Engine          | Graph traversal, path discovery, semantic query APIs, ranking, trust-aware retrieval. |
| 6     | Trust Integration     | Trust scoring, evidence resolution, explainability APIs, confidence propagation, verification. |
| 7     | Visualization         | Knowledge Explorer, graph viz, timeline views, trust inspector, evidence explorer. |
| 8     | Public Platform       | REST APIs, SDK integration, OpenAPI specs, developer docs, sample apps.       |
| 9     | Production Hardening   | Performance/load testing, security review, caching, observability, failure recovery, readiness review. |

Each phase requires: architecture design, ADR updates, implementation plan, risk
assessment, test strategy, acceptance criteria, documentation, validation results,
observability and security considerations.
