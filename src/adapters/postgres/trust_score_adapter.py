import uuid
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain import TrustScore
from src.domain.trust_score import TrustScoreComponents
from src.repositories import TrustScoreRepository
from .orm_models import TrustScoreORM


def _orm_to_domain(row: TrustScoreORM) -> TrustScore:
    return TrustScore(
        id=row.id,
        subject_id=row.subject_id,
        score=row.score,
        components=TrustScoreComponents(
            evidence_weight=row.evidence_weight,
            freshness_decay=row.freshness_decay,
            verification_bonus=row.verification_bonus,
            conflict_penalty=row.conflict_penalty,
            evidence_count=row.evidence_count,
        ),
        computed_at=row.computed_at,
        algorithm=row.algorithm,
    )


class PostgresTrustScoreAdapter(TrustScoreRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert(self, trust_score: TrustScore) -> TrustScore:
        result = await self._session.execute(
            select(TrustScoreORM).where(TrustScoreORM.subject_id == trust_score.subject_id)
        )
        row = result.scalar_one_or_none()
        if row:
            row.score = trust_score.score
            row.evidence_weight = trust_score.components.evidence_weight
            row.freshness_decay = trust_score.components.freshness_decay
            row.verification_bonus = trust_score.components.verification_bonus
            row.conflict_penalty = trust_score.components.conflict_penalty
            row.evidence_count = trust_score.components.evidence_count
            row.computed_at = trust_score.computed_at
            row.algorithm = trust_score.algorithm
        else:
            row = TrustScoreORM(
                id=trust_score.id,
                subject_id=trust_score.subject_id,
                score=trust_score.score,
                evidence_weight=trust_score.components.evidence_weight,
                freshness_decay=trust_score.components.freshness_decay,
                verification_bonus=trust_score.components.verification_bonus,
                conflict_penalty=trust_score.components.conflict_penalty,
                evidence_count=trust_score.components.evidence_count,
                computed_at=trust_score.computed_at,
                algorithm=trust_score.algorithm,
            )
            self._session.add(row)
        await self._session.flush()
        return _orm_to_domain(row)

    async def get_by_subject(self, subject_id: UUID) -> TrustScore | None:
        result = await self._session.execute(
            select(TrustScoreORM).where(TrustScoreORM.subject_id == subject_id)
        )
        row = result.scalar_one_or_none()
        return _orm_to_domain(row) if row else None

    async def get_by_id(self, score_id: UUID) -> TrustScore | None:
        result = await self._session.execute(
            select(TrustScoreORM).where(TrustScoreORM.id == score_id)
        )
        row = result.scalar_one_or_none()
        return _orm_to_domain(row) if row else None

    async def get_below_threshold(
        self, threshold: float, limit: int = 100
    ) -> list[TrustScore]:
        result = await self._session.execute(
            select(TrustScoreORM)
            .where(TrustScoreORM.score < threshold)
            .limit(limit)
        )
        return [_orm_to_domain(r) for r in result.scalars()]
