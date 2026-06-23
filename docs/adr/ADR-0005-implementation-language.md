# ADR-0005 — Implementation Language: Python + FastAPI

**Date:** 2026-06-23
**Status:** Accepted
**Deciders:** SCP Knowledge Graph Team

---

## Context

DEC-0001 deferred the implementation language choice to Phase 2. Phase 2 is the first
phase to produce runnable code. We need a language + framework that:

1. Supports async I/O (the storage adapter layer is async by design)
2. Has native type-safety that maps cleanly onto the Pydantic domain model
3. Carries strong graph library and vector search ecosystem (needed by Phase 5)
4. Auto-generates OpenAPI spec (required by Phase 8)
5. Has mature migration tooling for the storage backend

---

## Decision

**Language:** Python 3.11+
**API framework:** FastAPI
**Data validation:** Pydantic v2
**ORM:** SQLAlchemy 2.0 (async, declarative)
**Migrations:** Alembic
**Runtime:** Uvicorn (ASGI)

---

## Rationale

| Criterion | Python/FastAPI | TypeScript/NestJS | Go/Gin |
|-----------|---------------|-------------------|--------|
| Domain model → type-safe code | Pydantic v2 (direct mapping) | Zod / class-validator | struct tags |
| OpenAPI auto-gen | FastAPI native | Swagger decorators | swaggo |
| Graph library ecosystem | NetworkX, neo4j-driver, py2neo | Limited | None native |
| Async ORM | SQLAlchemy 2.0 async | TypeORM / Prisma | GORM (sync) |
| Vector search (Phase 5) | pgvector + langchain | pgvector-node | pgvector-go |
| Team familiarity | High | Medium | Low |

Python/FastAPI is the dominant choice for AI-adjacent systems. Pydantic v2 compiles
validators to Rust, achieving performance comparable to TypeScript.

---

## Consequences

- **Positive:** Fastest path to Phase 5 semantic search (embedding libraries are Python-first).
- **Positive:** Pydantic models in `src/domain/` are the single source of truth — no schema drift.
- **Negative:** Python GIL limits CPU-bound parallelism; mitigated by async I/O for DB-bound workloads.
- **Neutral:** Requires Python 3.11+ for performance and `tomllib` support.

---

## Python version policy

Minimum: Python 3.11. Target: Python 3.12 for production.
No compatibility shims for 3.10 or below.
