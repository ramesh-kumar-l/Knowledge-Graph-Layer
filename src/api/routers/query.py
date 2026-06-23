"""Phase 5 Query Engine — graph traversal, path discovery, semantic search stub.

Implements 6 query types from 13-query-model.md:
  1+2: point lookup + entity search — existing /entities router
  3: graph traversal — GET /{entity_id}/graph
  4: path discovery  — GET /{entity_id}/path/{to_entity_id}
  5: trust-filtered  — min_confidence param on all endpoints
  6: semantic search — stub, NOT_IMPLEMENTED (requires embedding API)
"""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from src.domain import Entity, Relationship, RelationshipType
from src.repositories import EntityRepository, RelationshipRepository
from src.services.graph_traversal_service import GraphTraversalService
from src.services.path_discovery_service import PathDiscoveryService
from src.api.deps import entity_repo, relationship_repo

router = APIRouter(prefix="/entities", tags=["query"])

EntityRepoDep = Annotated[EntityRepository, Depends(entity_repo)]
RelRepoDep = Annotated[RelationshipRepository, Depends(relationship_repo)]


class GraphResponse(BaseModel):
    nodes: list[Entity]
    edges: list[Relationship]
    truncated: bool
    node_count: int
    edge_count: int


class PathResponse(BaseModel):
    entities: list[Entity]
    relationships: list[Relationship]
    hop_count: int
    total_confidence: float


def _traversal_svc(e_repo: EntityRepoDep, r_repo: RelRepoDep) -> GraphTraversalService:
    return GraphTraversalService(e_repo, r_repo)


def _path_svc(e_repo: EntityRepoDep, r_repo: RelRepoDep) -> PathDiscoveryService:
    return PathDiscoveryService(e_repo, r_repo)


TraversalSvcDep = Annotated[GraphTraversalService, Depends(_traversal_svc)]
PathSvcDep = Annotated[PathDiscoveryService, Depends(_path_svc)]


@router.get("/semantic-search", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def semantic_search() -> dict:
    """Semantic similarity search — Phase 5b stub (requires embedding API)."""
    return {
        "detail": "Semantic search requires embedding API integration (Phase 5b).",
        "status": "NOT_IMPLEMENTED",
    }


@router.get("/{entity_id}/graph", response_model=GraphResponse)
async def get_entity_graph(
    entity_id: UUID,
    svc: TraversalSvcDep,
    e_repo: EntityRepoDep,
    max_depth: int = Query(3, ge=1, le=5),
    direction: str = Query("BOTH", pattern="^(OUTBOUND|INBOUND|BOTH)$"),
    rel_type: list[RelationshipType] | None = Query(None),
    min_confidence: float = Query(0.0, ge=0.0, le=1.0),
    limit: int = Query(100, ge=1, le=500),
) -> GraphResponse:
    entity = await e_repo.get_by_id(entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    result = await svc.traverse(
        start_entity_id=entity_id,
        max_depth=max_depth,
        direction=direction,
        rel_types=rel_type,
        min_confidence=min_confidence,
        limit=limit,
    )
    return GraphResponse(
        nodes=result.nodes,
        edges=result.edges,
        truncated=result.truncated,
        node_count=len(result.nodes),
        edge_count=len(result.edges),
    )


@router.get("/{entity_id}/neighbors", response_model=GraphResponse)
async def get_entity_neighbors(
    entity_id: UUID,
    svc: TraversalSvcDep,
    e_repo: EntityRepoDep,
    direction: str = Query("BOTH", pattern="^(OUTBOUND|INBOUND|BOTH)$"),
    rel_type: list[RelationshipType] | None = Query(None),
    min_confidence: float = Query(0.0, ge=0.0, le=1.0),
    limit: int = Query(100, ge=1, le=500),
) -> GraphResponse:
    entity = await e_repo.get_by_id(entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    result = await svc.get_neighbors(
        entity_id=entity_id,
        direction=direction,
        rel_types=rel_type,
        min_confidence=min_confidence,
        limit=limit,
    )
    return GraphResponse(
        nodes=result.nodes,
        edges=result.edges,
        truncated=result.truncated,
        node_count=len(result.nodes),
        edge_count=len(result.edges),
    )


@router.get("/{entity_id}/path/{to_entity_id}", response_model=PathResponse)
async def find_path(
    entity_id: UUID,
    to_entity_id: UUID,
    svc: PathSvcDep,
    e_repo: EntityRepoDep,
    max_hops: int = Query(4, ge=1, le=8),
    min_confidence: float = Query(0.0, ge=0.0, le=1.0),
    rel_type: list[RelationshipType] | None = Query(None),
) -> PathResponse:
    from_entity = await e_repo.get_by_id(entity_id)
    if not from_entity:
        raise HTTPException(status_code=404, detail="Source entity not found")
    to_entity = await e_repo.get_by_id(to_entity_id)
    if not to_entity:
        raise HTTPException(status_code=404, detail="Target entity not found")

    path = await svc.find_shortest_path(
        from_entity_id=entity_id,
        to_entity_id=to_entity_id,
        max_hops=max_hops,
        min_confidence=min_confidence,
        rel_types=rel_type,
    )
    if path is None:
        raise HTTPException(
            status_code=404, detail="No path found between the specified entities"
        )
    return PathResponse(
        entities=path.entities,
        relationships=path.relationships,
        hop_count=path.hop_count,
        total_confidence=path.total_confidence,
    )
