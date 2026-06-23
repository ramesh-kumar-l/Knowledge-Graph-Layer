import uuid
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain import Version, CreateVersionCommand, SubjectType
from src.repositories import VersionRepository
from .orm_models import VersionORM


def _orm_to_domain(row: VersionORM) -> Version:
    return Version(
        id=row.id,
        subject_type=SubjectType(row.subject_type),
        subject_id=row.subject_id,
        version=row.version,
        snapshot=row.snapshot,
        diff=row.diff,
        changed_by=row.changed_by,
        changed_at=row.changed_at,
        change_reason=row.change_reason or "",
    )


class PostgresVersionAdapter(VersionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, command: CreateVersionCommand) -> Version:
        row = VersionORM(
            id=uuid.uuid4(),
            subject_type=command.subject_type.value,
            subject_id=command.subject_id,
            version=command.version,
            snapshot=command.snapshot,
            diff=command.diff,
            changed_by=command.changed_by,
            change_reason=command.change_reason,
        )
        self._session.add(row)
        await self._session.flush()
        return _orm_to_domain(row)

    async def get_latest(
        self, subject_type: SubjectType, subject_id: UUID
    ) -> Version | None:
        result = await self._session.execute(
            select(VersionORM)
            .where(
                VersionORM.subject_type == subject_type.value,
                VersionORM.subject_id == subject_id,
            )
            .order_by(VersionORM.version.desc())
            .limit(1)
        )
        row = result.scalar_one_or_none()
        return _orm_to_domain(row) if row else None

    async def list_for_subject(
        self,
        subject_type: SubjectType,
        subject_id: UUID,
        offset: int = 0,
        limit: int = 50,
    ) -> list[Version]:
        result = await self._session.execute(
            select(VersionORM)
            .where(
                VersionORM.subject_type == subject_type.value,
                VersionORM.subject_id == subject_id,
            )
            .order_by(VersionORM.version.asc())
            .offset(offset)
            .limit(limit)
        )
        return [_orm_to_domain(r) for r in result.scalars()]

    async def get_by_version(self, subject_id: UUID, version: int) -> Version | None:
        result = await self._session.execute(
            select(VersionORM).where(
                VersionORM.subject_id == subject_id,
                VersionORM.version == version,
            )
        )
        row = result.scalar_one_or_none()
        return _orm_to_domain(row) if row else None
