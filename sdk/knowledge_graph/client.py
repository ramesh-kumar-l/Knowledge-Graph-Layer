"""KnowledgeGraphClient — async HTTP client for the SCP Knowledge Graph Layer API."""
from __future__ import annotations

from typing import Any
from uuid import UUID

import httpx

from knowledge_graph.models import (
    CreateEntityCommand,
    CreateRelationshipCommand,
    Entity,
    ExplainResponse,
    GraphResponse,
    MemoryRecord,
    PathResponse,
    Relationship,
    RelationshipType,
    ResolveConflictCommand,
    ResolutionDecision,
    UpdateEntityCommand,
)

_DEFAULT_TIMEOUT = 30.0


class KnowledgeGraphError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(f"HTTP {status_code}: {detail}")
        self.status_code = status_code
        self.detail = detail


class KnowledgeGraphClient:
    """Async client for all SCP Knowledge Graph Layer v1 endpoints.

    Usage::

        async with KnowledgeGraphClient("http://localhost:8000", api_key="sk-...") as client:
            entities = await client.list_entities()

    Or manage the session manually::

        client = KnowledgeGraphClient(base_url, api_key)
        await client.open()
        ...
        await client.close()
    """

    def __init__(
        self,
        base_url: str,
        api_key: str = "",
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> None:
        self._base = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout
        self._http: httpx.AsyncClient | None = None

    async def open(self) -> None:
        self._http = httpx.AsyncClient(timeout=self._timeout)

    async def close(self) -> None:
        if self._http:
            await self._http.aclose()
            self._http = None

    async def __aenter__(self) -> "KnowledgeGraphClient":
        await self.open()
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.close()

    # ── internals ──────────────────────────────────────────────────────────────

    def _headers(self) -> dict[str, str]:
        h = {"Accept": "application/json", "Content-Type": "application/json"}
        if self._api_key:
            h["X-Api-Key"] = self._api_key
        return h

    def _url(self, path: str) -> str:
        return f"{self._base}/v1/{path.lstrip('/')}"

    async def _request(
        self, method: str, path: str, *, params: dict | None = None, body: Any = None
    ) -> Any:
        assert self._http, "Call open() or use async context manager first."
        resp = await self._http.request(
            method,
            self._url(path),
            headers=self._headers(),
            params={k: v for k, v in (params or {}).items() if v is not None},
            json=body,
        )
        if not resp.is_success:
            detail = resp.json().get("detail", resp.text) if resp.content else resp.reason_phrase
            raise KnowledgeGraphError(resp.status_code, str(detail))
        if resp.status_code == 204 or not resp.content:
            return None
        return resp.json()

    # ── entities ───────────────────────────────────────────────────────────────

    async def list_entities(
        self, limit: int = 100, search: str | None = None
    ) -> list[Entity]:
        data = await self._request("GET", "entities/", params={"limit": limit, "search": search})
        return [Entity.model_validate(e) for e in data]

    async def get_entity(self, entity_id: str | UUID) -> Entity:
        data = await self._request("GET", f"entities/{entity_id}")
        return Entity.model_validate(data)

    async def create_entity(self, cmd: CreateEntityCommand) -> Entity:
        data = await self._request("POST", "entities/", body=cmd.model_dump(mode="json"))
        return Entity.model_validate(data)

    async def update_entity(self, entity_id: str | UUID, cmd: UpdateEntityCommand) -> Entity:
        data = await self._request(
            "PATCH", f"entities/{entity_id}",
            body=cmd.model_dump(mode="json", exclude_none=True),
        )
        return Entity.model_validate(data)

    async def delete_entity(self, entity_id: str | UUID) -> None:
        await self._request("DELETE", f"entities/{entity_id}")

    async def get_entity_versions(self, entity_id: str | UUID) -> list[dict]:
        return await self._request("GET", f"entities/{entity_id}/versions")

    # ── relationships ──────────────────────────────────────────────────────────

    async def list_relationships(
        self, entity_id: str | UUID | None = None, limit: int = 100
    ) -> list[Relationship]:
        data = await self._request(
            "GET", "relationships/",
            params={"entity_id": str(entity_id) if entity_id else None, "limit": limit},
        )
        return [Relationship.model_validate(r) for r in data]

    async def create_relationship(self, cmd: CreateRelationshipCommand) -> Relationship:
        data = await self._request("POST", "relationships/", body=cmd.model_dump(mode="json"))
        return Relationship.model_validate(data)

    # ── ingestion ──────────────────────────────────────────────────────────────

    async def ingest_memory_record(self, record: MemoryRecord) -> dict:
        return await self._request(
            "POST", "ingest/memory-record", body=record.model_dump(mode="json")
        )

    # ── graph queries ──────────────────────────────────────────────────────────

    async def get_entity_graph(
        self,
        entity_id: str | UUID,
        max_depth: int = 3,
        direction: str = "BOTH",
        rel_types: list[RelationshipType] | None = None,
        min_confidence: float = 0.0,
        limit: int = 100,
    ) -> GraphResponse:
        params: dict = {
            "max_depth": max_depth,
            "direction": direction,
            "min_confidence": min_confidence,
            "limit": limit,
        }
        if rel_types:
            params["rel_type"] = [r.value for r in rel_types]
        data = await self._request("GET", f"entities/{entity_id}/graph", params=params)
        return GraphResponse.model_validate(data)

    async def get_neighbors(
        self,
        entity_id: str | UUID,
        direction: str = "BOTH",
        min_confidence: float = 0.0,
        limit: int = 100,
    ) -> GraphResponse:
        data = await self._request(
            "GET", f"entities/{entity_id}/neighbors",
            params={"direction": direction, "min_confidence": min_confidence, "limit": limit},
        )
        return GraphResponse.model_validate(data)

    async def find_path(
        self,
        from_entity_id: str | UUID,
        to_entity_id: str | UUID,
        max_hops: int = 4,
        min_confidence: float = 0.0,
    ) -> PathResponse:
        data = await self._request(
            "GET", f"entities/{from_entity_id}/path/{to_entity_id}",
            params={"max_hops": max_hops, "min_confidence": min_confidence},
        )
        return PathResponse.model_validate(data)

    # ── explain ────────────────────────────────────────────────────────────────

    async def explain_entity(self, entity_id: str | UUID) -> ExplainResponse:
        data = await self._request("GET", f"explain/{entity_id}")
        return ExplainResponse.model_validate(data)

    # ── conflict ───────────────────────────────────────────────────────────────

    async def get_dispute_queue(self) -> list[Entity]:
        data = await self._request("GET", "conflict/queue")
        return [Entity.model_validate(e) for e in data]

    async def resolve_conflict(
        self,
        entity_id: str | UUID,
        decision: ResolutionDecision,
        resolved_by: str = "user",
        reason: str = "",
    ) -> Entity:
        cmd = ResolveConflictCommand(decision=decision, resolved_by=resolved_by, reason=reason)
        data = await self._request(
            "POST", f"conflict/{entity_id}/resolve", body=cmd.model_dump(mode="json")
        )
        return Entity.model_validate(data)
