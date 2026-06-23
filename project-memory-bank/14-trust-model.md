# 14 — Trust Model

**Status:** Phase 1 — foundations complete (2026-06-23). Full propagation + framework in Phase 6.

## Core principle
Every fact in the graph MUST carry trust metadata. No opaque knowledge is allowed.
For any fact, the system must always answer:

> *Why does this exist? What evidence supports it? Where did it come from? How trustworthy is it?*

---

## Verification states

| State | Meaning | Entry condition |
|-------|---------|-----------------|
| UNVERIFIED | Default on creation | New entity/relationship from any source |
| INFERRED | System-derived; not explicitly confirmed | Fuzzy match, cross-session inference |
| VERIFIED | Explicitly confirmed (human or high-confidence system) | Manual review, exact source match |
| DISPUTED | Conflicting evidence found | Contradiction detected across evidence records |

State transitions are logged as Version history. DISPUTED requires resolution
before it can transition to VERIFIED.

---

## Confidence score

Range: `[0.0, 1.0]`

| Range | Interpretation |
|-------|---------------|
| 0.0 – 0.3 | Very low — likely noise; excluded from default queries |
| 0.3 – 0.5 | Low — possible, unverified |
| 0.5 – 0.7 | Moderate — reasonable inference |
| 0.7 – 0.9 | High — strong evidence |
| 0.9 – 1.0 | Very high — explicitly verified |

**Default query minimum:** `0.5`
Confidence is always computed from Evidence; it is never set directly by a caller.

---

## TrustScore formula

```
score = clamp(
    (evidenceWeight    × 0.50)
  + (freshnessDecay    × 0.20)
  + (verificationBonus × 0.20)
  - (conflictPenalty   × 0.10)
, 0.0, 1.0)
```

### evidenceWeight
Weighted average of confidence across all attached Evidence records.
```
evidenceWeight = Σ(e.confidence × w(e.sourceType)) / Σ(w(e.sourceType))
```

Source type weights:
```
USER_INPUT:  1.0
DOCUMENT:    0.9
MEMORY:      0.8
SYSTEM:      0.7
INFERENCE:   0.6
```

### freshnessDecay
Linear decay from the most recent evidence update over a 90-day window.
```
ageDays       = (now - mostRecentEvidenceAt) / 86400
freshnessDecay = max(0.0, 1.0 - (ageDays / 90.0))
```
Configurable decay window; default 90 days. Facts older than the window have
`freshnessDecay = 0` but are NOT deleted — they remain queryable with `includeFresh = false`.

### verificationBonus
```
VERIFIED:   +0.20 (applied before clamp)
INFERRED:   +0.00
UNVERIFIED: +0.00
DISPUTED:   (handled by conflictPenalty)
```

### conflictPenalty
```
conflictPenalty = min(1.0, disputedEvidenceCount × 0.10)
```
Each DISPUTED evidence record contributes -0.10 to the score.

---

## Evidence source weights

| Source type | Weight | Notes |
|-------------|--------|-------|
| USER_INPUT | 1.0 | Explicit human assertion — highest weight |
| DOCUMENT | 0.9 | Sourced from a parsed, verifiable document |
| MEMORY | 0.8 | Extracted from SCP Memory Core |
| SYSTEM | 0.7 | System-generated (schema inference, automated rule) |
| INFERENCE | 0.6 | Derived by AI/model — lowest weight |

---

## Conflict detection rules

A conflict is raised when:
1. Two Evidence records assert different values for the same entity attribute.
2. Confidence of an existing fact drops below 0.3 after new contradicting evidence.
3. A user explicitly marks an assertion as incorrect.

**Conflict policy:**
- Both evidence records are retained (never discard sourced facts).
- Conflicting attribute's `verificationState` → DISPUTED.
- Emit `KnowledgeConflictDetected { entityId, attribute, evidenceIds[] }`.
- Surface conflicts in query results with `{ conflict: true, conflictingEvidenceIds }` when `includeConflicts = true`.
- Never silently resolve — human or trust-framework resolution is required.

---

## Freshness policy

- Facts with no evidence updates for > 180 days → automatically flagged `STALE`.
- STALE is a derived query-time flag, not a VerificationState.
- Stale entities remain in the graph; excluded from results by default.
- Override: `includeFresh: false` in query parameters to include stale facts.

---

## Trust propagation (Phase 6 — stub)

For multi-hop paths A → B → C, path confidence uses pessimistic propagation:
```
pathConfidence = min(A.confidence, A_B_rel.confidence, B_C_rel.confidence, C.confidence)
```
The weakest link determines path strength. Alternative strategies (geometric mean,
context-aware) are Phase 6 design choices.

---

## Observability requirements

TrustScore computation must emit:
- `knowledge.trust_score_computed { subjectId, score, components, algorithm, computedAt }`
- `knowledge.conflict_detected { entityId, attribute, evidenceIds }`
- `knowledge.entity_verified { entityId, verifiedBy, verifiedAt }`
- `knowledge.entity_disputed { entityId, attribute, reason }`

All events carry `subjectId`, `algorithm`, `score`, and `computedAt`.
