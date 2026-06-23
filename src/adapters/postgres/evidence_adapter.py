import uuid
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain import (
    Evidence, CreateEvidenceCommand,
    SubjectType, EvidenceSourceType, VerificationState,
)
from src.repositories import EvidenceRepository
from .orm_models import EvidenceORM


class DuplicateEvidenceError(Exception):
    """Raised when (subject_id, source_id) already exists."""


def _orm_to_domain(row: EvidenceORM) -> Evidence:
    return Evidence(
        id=row.id,
        subject_type=SubjectType(row.subject_type),
        subject_id=row.subject_id,
        source_type=EvidenceSourceType(row.source_type),
        source_id=row.source_id,
        content=row.content,
        confidence=row.confidence,
        extracted_at=row.extracted_at,
        extractor_id=row.extractor_id,
        verification_state=VerificationState(row.verification_state),
        metadata=row.metadata_ or {},
    )


class PostgresEvidenceAdapter(EvidenceRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, command: CreateEvidenceCommand) -> Evidence:
        if await self.exists(command.subject_id, command.source_id):
            raise DuplicateEvidenceError(
                f"Evidence for subject={command.subject_id} source={command.source_id} already exists"
            )
        row = EvidenceORM(
            id=uuid.uuid4(),
            subject_type=command.subject_type.value,
            subject_id=command.subject_id,
            source_type=command.source_type.value,
            source_id=command.source_id,
            content=command.content,
            confidence=command.confidence,
            extractor_id=command.extractor_id,
            verification_state=command.verification_state.value,
            metadata_=command.metadata,
        )
        self._session.add(row)
        await self._session.flush()
        return _orm_to_domain(row)

    async def get_by_id(self, evidence_id: UUID) -> Evidence | None:
        result = await self._session.execute(
            select(EvidenceORM).where(EvidenceORM.id == evidence_id)
        )
        row = result.scalar_one_or_none()
        return _orm_to_domain(row) if row else None

    async def get_for_subject(
        self, subject_type: SubjectType, subject_id: UUID
    ) -> list[Evidence]:
        result = await self._session.execute(
            select(EvidenceORM).where(
                EvidenceORM.subject_type == subject_type.value,
                EvidenceORM.subject_id == subject_id,
            )
        )
        return [_orm_to_domain(r) for r in result.scalars()]

    async def exists(self, subject_id: UUID, source_id: str) -> bool:
        result = await self._session.execute(
            select(func.count()).where(
                EvidenceORM.subject_id == subject_id,
                EvidenceORM.source_id == source_id,
            )
        )
        return result.scalar_one() > 0

    async def count_disputed(self, subject_id: UUID) -> int:
        result = await self._session.execute(
            select(func.count()).where(
                EvidenceORM.subject_id == subject_id,
                EvidenceORM.verification_state == VerificationState.DISPUTED.value,
            )
        )
        return result.scalar_one()

    async def exists_by_source_id(self, source_id: str) -> bool:
        result = await self._session.execute(
            select(func.count()).where(EvidenceORM.source_id == source_id)
        )
        return result.scalar_one() > 0
