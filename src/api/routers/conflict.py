"""Phase 7 — Conflict resolution REST endpoints for the Knowledge Explorer UI.

Exposes ConflictResolutionService (Phase 6) over HTTP so the UI can:
  GET  /v1/conflict/queue          — list all DISPUTED entities
  POST /v1/conflict/{id}/resolve   — ACCEPT (→ VERIFIED) or REJECT (→ UNVERIFIED)
"""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from src.domain import Entity, VerificationState
from src.repositories import EntityRepository
from src.services.conflict_resolution_service import (
    ConflictResolutionService,
    ConflictResolutionError,
    ResolutionDecision,
)
from src.api.deps import entity_repo, conflict_resolution_service

router = APIRouter(prefix="/conflict", tags=["conflict"])

EntityRepoDep = Annotated[EntityRepository, Depends(entity_repo)]
ConflictSvcDep = Annotated[ConflictResolutionService, Depends(conflict_resolution_service)]


class ResolveRequest(BaseModel):
    decision: ResolutionDecision
    resolved_by: str = "user"
    reason: str = ""


@router.get("/queue", response_model=list[Entity])
async def get_dispute_queue(repo: EntityRepoDep) -> list[Entity]:
    """Return all active DISPUTED entities."""
    return await repo.list_by_verification_state(VerificationState.DISPUTED)


@router.post("/{entity_id}/resolve", response_model=Entity)
async def resolve_conflict(
    entity_id: UUID,
    body: ResolveRequest,
    svc: ConflictSvcDep,
) -> Entity:
    """Resolve a DISPUTED entity: ACCEPT → VERIFIED, REJECT → UNVERIFIED."""
    try:
        return await svc.resolve(
            entity_id=entity_id,
            decision=body.decision,
            resolved_by=body.resolved_by,
            reason=body.reason,
        )
    except ConflictResolutionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
