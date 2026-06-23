"""FastAPI dependency injection — wires adapters to repositories."""
from typing import Annotated, AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.adapters.postgres.connection import get_session
from src.adapters.postgres.entity_adapter import PostgresEntityAdapter
from src.adapters.postgres.relationship_adapter import PostgresRelationshipAdapter
from src.adapters.postgres.evidence_adapter import PostgresEvidenceAdapter
from src.adapters.postgres.provenance_adapter import PostgresProvenanceAdapter
from src.adapters.postgres.trust_score_adapter import PostgresTrustScoreAdapter
from src.adapters.postgres.version_adapter import PostgresVersionAdapter
from src.repositories import (
    EntityRepository, RelationshipRepository,
    EvidenceRepository, ProvenanceRepository,
    TrustScoreRepository, VersionRepository,
)
from src.services import TrustScoreService, VersionService

SessionDep = Annotated[AsyncSession, Depends(get_session)]


def entity_repo(session: SessionDep) -> EntityRepository:
    return PostgresEntityAdapter(session)


def relationship_repo(session: SessionDep) -> RelationshipRepository:
    return PostgresRelationshipAdapter(session)


def evidence_repo(session: SessionDep) -> EvidenceRepository:
    return PostgresEvidenceAdapter(session)


def provenance_repo(session: SessionDep) -> ProvenanceRepository:
    return PostgresProvenanceAdapter(session)


def trust_score_repo(session: SessionDep) -> TrustScoreRepository:
    return PostgresTrustScoreAdapter(session)


def version_repo(session: SessionDep) -> VersionRepository:
    return PostgresVersionAdapter(session)


def trust_score_service(
    ev_repo: Annotated[EvidenceRepository, Depends(evidence_repo)],
    ts_repo: Annotated[TrustScoreRepository, Depends(trust_score_repo)],
) -> TrustScoreService:
    return TrustScoreService(ev_repo, ts_repo)


def version_service(
    v_repo: Annotated[VersionRepository, Depends(version_repo)],
) -> VersionService:
    return VersionService(v_repo)
