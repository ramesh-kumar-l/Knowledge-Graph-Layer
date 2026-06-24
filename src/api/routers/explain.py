"""GET /v1/explain/{entity_id} — full trust breakdown for an entity.

Returns:
  - Entity metadata + verification state
  - TrustScore with all formula components
  - Attached Evidence records
  - Provenance chain
  - Version history filtered to conflict-related transitions
"""
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from src.api.deps import (
    entity_repo, evidence_repo, provenance_repo,
    trust_score_repo, version_repo,
)
from src.domain import SubjectType, VerificationState
from src.repositories import (
    EntityRepository, EvidenceRepository, ProvenanceRepository,
    TrustScoreRepository, VersionRepository,
)
from typing import Annotated

router = APIRouter(prefix="/explain", tags=["explain"])

EntityRepoDep = Annotated[EntityRepository, Depends(entity_repo)]
EvidenceRepoDep = Annotated[EvidenceRepository, Depends(evidence_repo)]
ProvenanceRepoDep = Annotated[ProvenanceRepository, Depends(provenance_repo)]
TrustRepoDep = Annotated[TrustScoreRepository, Depends(trust_score_repo)]
VersionRepoDep = Annotated[VersionRepository, Depends(version_repo)]


class TrustComponentsResponse(BaseModel):
    evidence_weight: float
    freshness_decay: float
    verification_bonus: float
    conflict_penalty: float
    evidence_count: int


class TrustScoreResponse(BaseModel):
    score: float
    components: TrustComponentsResponse
    algorithm: str
    computed_at: str


class ConflictEvent(BaseModel):
    version: int
    change_reason: str
    changed_by: str
    changed_at: str


class ExplainResponse(BaseModel):
    entity_id: UUID
    entity_name: str
    entity_type: str
    verification_state: str
    is_disputed: bool
    trust_score: TrustScoreResponse | None
    evidence: list[dict[str, Any]]
    provenance: dict[str, Any] | None
    conflict_history: list[ConflictEvent]


@router.get("/{entity_id}", response_model=ExplainResponse)
async def explain_entity(
    entity_id: UUID,
    entity_repo_dep: EntityRepoDep,
    evidence_repo_dep: EvidenceRepoDep,
    provenance_repo_dep: ProvenanceRepoDep,
    trust_repo_dep: TrustRepoDep,
    version_repo_dep: VersionRepoDep,
) -> ExplainResponse:
    """Return full trust breakdown for an entity."""
    entity = await entity_repo_dep.get_by_id(entity_id)
    if not entity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entity not found")

    # Fetch all supporting data concurrently (sequential for SQLite safety)
    evidence_list = await evidence_repo_dep.get_for_subject(SubjectType.ENTITY, entity_id)
    provenance = await provenance_repo_dep.get_by_subject(entity_id)
    trust_score = await trust_repo_dep.get_by_subject(entity_id)
    versions = await version_repo_dep.list_for_subject(
        SubjectType.ENTITY, entity_id, limit=100
    )

    # Filter version history to conflict-related events only
    conflict_history = [
        ConflictEvent(
            version=v.version,
            change_reason=v.change_reason or "",
            changed_by=v.changed_by,
            changed_at=v.changed_at.isoformat(),
        )
        for v in versions
        if v.change_reason and "conflict" in v.change_reason
    ]

    trust_response = None
    if trust_score:
        trust_response = TrustScoreResponse(
            score=trust_score.score,
            components=TrustComponentsResponse(
                evidence_weight=trust_score.components.evidence_weight,
                freshness_decay=trust_score.components.freshness_decay,
                verification_bonus=trust_score.components.verification_bonus,
                conflict_penalty=trust_score.components.conflict_penalty,
                evidence_count=trust_score.components.evidence_count,
            ),
            algorithm=trust_score.algorithm,
            computed_at=trust_score.computed_at.isoformat(),
        )

    evidence_dicts = [
        {
            "id": str(ev.id),
            "source_type": ev.source_type,
            "source_id": ev.source_id,
            "confidence": ev.confidence,
            "verification_state": ev.verification_state,
            "extracted_at": ev.extracted_at.isoformat(),
            "content_preview": ev.content[:200] if ev.content else "",
        }
        for ev in evidence_list
    ]

    provenance_dict = None
    if provenance:
        provenance_dict = {
            "id": str(provenance.id),
            "origin": provenance.origin,
            "extraction_method": provenance.extraction_method,
            "agent_id": provenance.agent_id,
            "session_id": str(provenance.session_id) if provenance.session_id else None,
            "timestamp": provenance.timestamp.isoformat(),
        }

    return ExplainResponse(
        entity_id=entity.id,
        entity_name=entity.name,
        entity_type=entity.type,
        verification_state=entity.verification_state,
        is_disputed=entity.verification_state == VerificationState.DISPUTED,
        trust_score=trust_response,
        evidence=evidence_dicts,
        provenance=provenance_dict,
        conflict_history=conflict_history,
    )
