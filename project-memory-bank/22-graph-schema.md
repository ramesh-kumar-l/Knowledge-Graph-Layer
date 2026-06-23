# 22 — Graph Schema

**Status:** Not started — Phase 1 (logical) → Phase 2 (physical).

## Purpose
Define the graph schema. In Phase 1 this is the **logical** schema (entity/relationship
types, fields, constraints) expressed independently of any storage engine. The
**physical** schema/adapter follows in Phase 2.

## Direction (from DEC-0002)
- Logical schema stays backend-neutral (ports-and-adapters).
- No commitment to a specific query language or DB until the Phase 2 ADR.

## To be defined in Phase 1
- Logical node/edge types and required fields.
- Validity constraints between entity and relationship types.
- Trust, evidence, and provenance attachment points on the schema.

_(Placeholder — no concrete schema yet.)_
