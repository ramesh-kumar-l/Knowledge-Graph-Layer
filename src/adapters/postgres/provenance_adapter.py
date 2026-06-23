import uuid
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain import Provenance, CreateProvenanceCommand, SubjectType
from src.domain.evidence import TransformationStep
from src.repositories import ProvenanceRepository
from .orm_models import ProvenanceORM


class DuplicateProvenanceError(Exception):
    """Raised when a provenance record for this subject already exists."""


def _orm_to_domain(row: ProvenanceORM) -> Provenance:
    steps = [
        TransformationStep(**s) for s in (row.transformations or [])
    ]
    return Provenance(
        id=row.id,
        subject_type=SubjectType(row.subject_type),
        subject_id=row.subject_id,
        origin=row.origin,
        extraction_method=row.extraction_method,
        transformations=steps,
        raw_source_ref=row.raw_source_ref,
        session_id=row.session_id,
        agent_id=row.agent_id,
        timestamp=row.timestamp,
    )


class PostgresProvenanceAdapter(ProvenanceRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, command: CreateProvenanceCommand) -> Provenance:
        existing = await self.get_by_subject(command.subject_id)
        if existing:
            raise DuplicateProvenanceError(
                f"Provenance for subject={command.subject_id} already exists"
            )
        row = ProvenanceORM(
            id=uuid.uuid4(),
            subject_type=command.subject_type.value,
            subject_id=command.subject_id,
            origin=command.origin,
            extraction_method=command.extraction_method,
            transformations=[s.model_dump(mode="json") for s in command.transformations],
            raw_source_ref=command.raw_source_ref,
            session_id=command.session_id,
            agent_id=command.agent_id,
        )
        self._session.add(row)
        await self._session.flush()
        return _orm_to_domain(row)

    async def get_by_subject(self, subject_id: UUID) -> Provenance | None:
        result = await self._session.execute(
            select(ProvenanceORM).where(ProvenanceORM.subject_id == subject_id)
        )
        row = result.scalar_one_or_none()
        return _orm_to_domain(row) if row else None

    async def get_by_id(self, provenance_id: UUID) -> Provenance | None:
        result = await self._session.execute(
            select(ProvenanceORM).where(ProvenanceORM.id == provenance_id)
        )
        row = result.scalar_one_or_none()
        return _orm_to_domain(row) if row else None
