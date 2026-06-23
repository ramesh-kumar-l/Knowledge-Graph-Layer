"""Ingestion API — accepts SCP Memory Core records, runs Entity Engine pipeline."""
from typing import Annotated

from fastapi import APIRouter, Depends

from src.api.deps import (
    entity_repo, evidence_repo, provenance_repo,
    trust_score_service, version_service,
)
from src.repositories import EntityRepository, EvidenceRepository, ProvenanceRepository
from src.services import TrustScoreService, VersionService
from src.ingestion.entity_pipeline import EntityIngestionPipeline
from src.ingestion.models import MemoryRecord, IngestionResult

router = APIRouter(prefix="/ingest", tags=["ingestion"])


def _pipeline(
    e_repo: Annotated[EntityRepository, Depends(entity_repo)],
    ev_repo: Annotated[EvidenceRepository, Depends(evidence_repo)],
    prov_repo: Annotated[ProvenanceRepository, Depends(provenance_repo)],
    ts_svc: Annotated[TrustScoreService, Depends(trust_score_service)],
    ver_svc: Annotated[VersionService, Depends(version_service)],
) -> EntityIngestionPipeline:
    return EntityIngestionPipeline(
        entity_repo=e_repo,
        evidence_repo=ev_repo,
        provenance_repo=prov_repo,
        trust_svc=ts_svc,
        version_svc=ver_svc,
    )


PipelineDep = Annotated[EntityIngestionPipeline, Depends(_pipeline)]


@router.post("/memory-record", response_model=IngestionResult, status_code=200)
async def ingest_memory_record(
    record: MemoryRecord,
    pipeline: PipelineDep,
) -> IngestionResult:
    """Ingest a single SCP Memory Core record.

    Idempotent: re-submitting the same record.id returns status=SKIPPED_DUPLICATE.
    """
    return await pipeline.ingest(record)
