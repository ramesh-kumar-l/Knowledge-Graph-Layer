"""End-to-end demo: ingest two memory records, query the resulting knowledge graph.

Prerequisites:
    1. Backend running: uvicorn src.api.main:app --reload --port 8000
    2. (Optional) Set API_KEYS=sk-demo on the server and pass api_key="sk-demo" below.

Run:
    python examples/ingest_and_query.py
"""
import asyncio
import sys

# Allow running from repo root without installing the SDK
sys.path.insert(0, "sdk")

from knowledge_graph import (
    KnowledgeGraphClient,
    KnowledgeGraphError,
    MemoryRecord,
)

BASE_URL = "http://localhost:8000"
API_KEY = ""  # set to your key if API_KEYS is configured on the server


async def main() -> None:
    async with KnowledgeGraphClient(BASE_URL, api_key=API_KEY) as client:
        # ── 1. Ingest two memory records ────────────────────────────────────
        print("Ingesting memory records...")
        result_a = await client.ingest_memory_record(
            MemoryRecord(
                content="Alice is the lead engineer at Acme Corp and manages the platform team.",
                source="slack",
                author="system",
                tags=["people", "org"],
            )
        )
        print(f"  Record A: {result_a}")

        result_b = await client.ingest_memory_record(
            MemoryRecord(
                content="Acme Corp is building a new data platform project called DataFlow.",
                source="confluence",
                author="system",
                tags=["projects", "org"],
            )
        )
        print(f"  Record B: {result_b}")

        # ── 2. List extracted entities ───────────────────────────────────────
        print("\nListing extracted entities...")
        entities = await client.list_entities(limit=20)
        for e in entities:
            print(f"  [{e.type.value}] {e.name}  confidence={e.confidence:.2f}  state={e.verification_state.value}")

        if not entities:
            print("  No entities found — is the backend running with a live database?")
            return

        # ── 3. Query graph for the first entity ──────────────────────────────
        seed = entities[0]
        print(f"\nGraph traversal from: {seed.name} ({seed.id}) ...")
        graph = await client.get_entity_graph(seed.id, max_depth=2, min_confidence=0.3)
        print(f"  Nodes: {graph.node_count}  Edges: {graph.edge_count}  Truncated: {graph.truncated}")

        # ── 4. Explain trust score ───────────────────────────────────────────
        print(f"\nTrust explanation for: {seed.name} ...")
        try:
            explain = await client.explain_entity(seed.id)
            ts = explain.trust_score
            print(f"  Overall confidence : {ts.overall_confidence:.4f}")
            print(f"  Evidence weight    : {ts.components.evidence_weight:.4f}")
            print(f"  Freshness decay    : {ts.components.freshness_decay:.4f}")
            print(f"  Verification bonus : {ts.components.verification_bonus:.4f}")
            print(f"  Conflict penalty   : {ts.components.conflict_penalty:.4f}")
            print(f"  Evidence items     : {len(explain.evidence)}")
        except KnowledgeGraphError as e:
            print(f"  (explain not available: {e})")

        # ── 5. Check conflict queue ──────────────────────────────────────────
        print("\nConflict queue (DISPUTED entities)...")
        disputed = await client.get_dispute_queue()
        if disputed:
            for d in disputed:
                print(f"  DISPUTED: {d.name} ({d.id})")
        else:
            print("  No disputed entities.")

        print("\nDone.")


if __name__ == "__main__":
    asyncio.run(main())
