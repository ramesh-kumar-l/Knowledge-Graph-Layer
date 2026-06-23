# 14 — Trust Model

**Status:** Not started — Phase 1 (foundations) → Phase 6 (full integration).

## Purpose
Define mandatory trust semantics. Every graph fact must carry: Confidence Score,
Evidence, Provenance, Verification State, and Freshness. No opaque knowledge is allowed.

The system must always answer, for any fact:
- Why does this fact exist?
- What evidence supports it?
- Where did it come from?
- How trustworthy is it?

## To be defined in Phase 1
- Confidence score representation and range.
- Evidence and Provenance field definitions (cross-ref `10-domain-model.md`).
- Verification state lifecycle.

## To be defined in Phase 6
- Confidence propagation across multi-hop paths.
- Trust scoring and verification framework.

_(Placeholder — no design content yet.)_
