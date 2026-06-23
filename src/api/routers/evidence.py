from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.domain import Evidence, CreateEvidenceCommand, SubjectType
from src.repositories import EvidenceRepository
from src.services import TrustScoreService
from src.adapters.postgres.evidence_adapter import DuplicateEvidenceError
from src.api.deps import evidence_repo, trust_score_service

router = APIRouter(prefix="/evidence", tags=["evidence"])

EvidenceRepoDep = Annotated[EvidenceRepository, Depends(evidence_repo)]
TrustSvcDep = Annotated[TrustScoreService, Depends(trust_score_service)]


@router.post("/", response_model=Evidence, status_code=status.HTTP_201_CREATED)
async def create_evidence(
    command: CreateEvidenceCommand,
    repo: EvidenceRepoDep,
    trust_svc: TrustSvcDep,
) -> Evidence:
    try:
        evidence = await repo.create(command)
    except DuplicateEvidenceError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    # Recompute trust score for the subject after new evidence is attached
    from src.domain import VerificationState
    await trust_svc.compute_and_persist(
        subject_type=command.subject_type,
        subject_id=command.subject_id,
        verification_state=command.verification_state,
    )
    return evidence


@router.get("/{evidence_id}", response_model=Evidence)
async def get_evidence(evidence_id: UUID, repo: EvidenceRepoDep) -> Evidence:
    ev = await repo.get_by_id(evidence_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Evidence not found")
    return ev


@router.get("/subject/{subject_id}", response_model=list[Evidence])
async def get_evidence_for_subject(
    subject_id: UUID,
    repo: EvidenceRepoDep,
    subject_type: SubjectType = Query(SubjectType.ENTITY),
) -> list[Evidence]:
    return await repo.get_for_subject(subject_type, subject_id)


@router.get("/check-idempotency/")
async def check_idempotency(
    repo: EvidenceRepoDep,
    subject_id: UUID = Query(...),
    source_id: str = Query(..., min_length=1),
) -> dict:
    exists = await repo.exists(subject_id, source_id)
    return {"exists": exists, "subject_id": str(subject_id), "source_id": source_id}
