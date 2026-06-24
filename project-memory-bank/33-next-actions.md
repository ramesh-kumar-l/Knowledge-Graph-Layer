# 33 — Next Actions

Phase 6 is complete. Awaiting approval for Phase 7.

## On approval: begin Phase 7 — Visualization

Phase 7 adds the Knowledge Explorer UI — a browser-based interface for exploring
entities, traversing the graph, inspecting trust scores, and resolving conflicts.

### Phase 7 deliverables

1. **Technology stack** — React + TypeScript + Vite + Tailwind CSS (Linear/Stripe aesthetic)
2. **Graph view** — interactive node/edge canvas (react-flow or d3-force); color-coded by entity type; edge labels with relationship type + confidence
3. **Entity inspector** — side panel: trust score breakdown, evidence list, provenance, conflict history; links to conflict resolution actions
4. **Timeline view** — version history visualized per entity (audit trail)
5. **Trust filter bar** — global min_confidence slider; filter by verification state; rel_type facets
6. **Conflict resolution UI** — list of DISPUTED entities; Accept / Reject buttons wired to the Phase 6 conflict resolution API

### Phase 7 file structure
```
ui/
  src/
    components/
      GraphCanvas.tsx        (< 200 lines)
      EntityInspector.tsx    (< 200 lines)
      TrustBreakdown.tsx     (< 150 lines)
      ConflictQueue.tsx      (< 150 lines)
    pages/
      KnowledgeExplorer.tsx  (< 100 lines)
    api/
      client.ts              (< 100 lines — typed fetch wrappers)
  vite.config.ts
  package.json
```

### Phase 7 exit criteria
- Knowledge Explorer loads in browser; graph renders connected entities from real API
- Entity inspector shows trust score, evidence, provenance for any selected node
- Trust filter slider filters visible nodes by confidence threshold
- DISPUTED entities surfaced; Accept/Reject resolves via Phase 6 API
- Linear/Stripe-quality visual bar (premium, minimal, accessible)

_Do not proceed without explicit user approval (phase-execution model)._
