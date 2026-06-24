"""Phase 9 performance benchmark.

Measures:
  1. Entity extraction throughput -- pure CPU (regex + string ops).
     Target: >=10,000 entities/sec extracted across all records.
  2. API latency via in-process ASGI test client (no network, in-memory SQLite).
     Target: p99 < 100ms for /health endpoint.

Run:
    python scripts/benchmark_ingestion.py
"""
import statistics
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def bench_extraction(iterations: int = 50_000) -> None:
    from src.ingestion.entity_extractor import EntityExtractor
    from src.ingestion.models import MemoryRecord

    extractor = EntityExtractor()
    record = MemoryRecord(
        id=str(uuid.uuid4()),
        content=(
            "Alice is a senior engineer at Acme Corp working on Project Phoenix. "
            "She collaborates with Bob (product manager) and Carol (designer) to "
            "deliver the authentication module by Q3. The project uses Python and React."
        ),
        timestamp=datetime.now(timezone.utc),
        session_id=uuid.uuid4(),
        agent_id="bench-agent",
    )

    start = time.perf_counter()
    total_entities = 0
    for _ in range(iterations):
        candidates = extractor.extract(record)
        total_entities += len(candidates)
    elapsed = time.perf_counter() - start

    rec_rate = iterations / elapsed
    ent_rate = total_entities / elapsed
    avg = total_entities / iterations
    status = "PASS" if ent_rate >= 10_000 else "FAIL"
    print(f"\n-- Entity Extraction Throughput ------------------")
    print(f"  Iterations        : {iterations:,}")
    print(f"  Elapsed           : {elapsed:.3f}s")
    print(f"  Record/sec        : {rec_rate:,.0f}")
    print(f"  Entity/sec        : {ent_rate:,.0f}  [{status} -- target >=10,000]")
    print(f"  Avg entities/rec  : {avg:.1f}")
    if status == "FAIL":
        print(f"  WARNING: entity/sec {ent_rate:.0f} < 10,000")


def bench_api_latency(samples: int = 200) -> None:
    import os
    import asyncio
    import httpx

    os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    os.environ.pop("API_KEYS", None)

    from src.api.main import app

    async def _run() -> list[float]:
        latencies: list[float] = []
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test", follow_redirects=True
        ) as client:
            for _ in range(5):
                await client.get("/health")
            for _ in range(samples):
                t0 = time.perf_counter()
                resp = await client.get("/health")
                t1 = time.perf_counter()
                assert resp.status_code == 200, f"Unexpected {resp.status_code}"
                latencies.append((t1 - t0) * 1000)
        return latencies

    latencies = asyncio.run(_run())
    latencies.sort()
    p50 = statistics.median(latencies)
    p99 = latencies[int(len(latencies) * 0.99)]
    p_max = max(latencies)
    status = "PASS" if p99 < 100 else "FAIL"
    print(f"\n-- /health Latency (in-process ASGI, n={samples}) -----------")
    print(f"  p50  : {p50:.2f} ms")
    print(f"  p99  : {p99:.2f} ms  [{status} -- target <100ms]")
    print(f"  max  : {p_max:.2f} ms")
    if status == "FAIL":
        print(f"  WARNING: p99 {p99:.2f}ms >= 100ms")


if __name__ == "__main__":
    bench_extraction()
    bench_api_latency()
    print("\nBenchmark complete.")
