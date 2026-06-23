import uuid
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, or_, update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain import (
    Relationship, CreateRelationshipCommand,
    RelationshipType, Direction, VerificationState,
)
from src.repositories import RelationshipRepository
from .orm_models import RelationshipORM


def _orm_to_domain(row: RelationshipORM) -> Relationship:
    return Relationship(
        id=row.id,
        type=RelationshipType(row.type),
        from_entity_id=row.from_entity_id,
        to_entity_id=row.to_entity_id,
        direction=Direction(row.direction),
        attributes=row.attributes or {},
        confidence=row.confidence,
        verification_state=VerificationState(row.verification_state),
        evidence_ids=row.evidence_ids or [],
        provenance_id=row.provenance_id,
        strength=row.strength,
        version=row.version,
        created_at=row.created_at,
        updated_at=row.updated_at,
        is_active=row.is_active,
    )


class PostgresRelationshipAdapter(RelationshipRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, command: CreateRelationshipCommand) -> Relationship:
        row = RelationshipORM(
            id=uuid.uuid4(),
            type=command.type.value,
            from_entity_id=command.from_entity_id,
            to_entity_id=command.to_entity_id,
            direction=command.direction.value,
            attributes=command.attributes,
            confidence=0.0,
            verification_state=VerificationState.UNVERIFIED.value,
            evidence_ids=[],
            strength=command.strength,
            version=1,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            is_active=True,
        )
        self._session.add(row)
        await self._session.flush()
        return _orm_to_domain(row)

    async def get_by_id(self, rel_id: UUID) -> Relationship | None:
        result = await self._session.execute(
            select(RelationshipORM).where(
                RelationshipORM.id == rel_id,
                RelationshipORM.is_active.is_(True),
            )
        )
        row = result.scalar_one_or_none()
        return _orm_to_domain(row) if row else None

    async def get_outbound(
        self,
        from_entity_id: UUID,
        rel_type: RelationshipType | None = None,
        limit: int = 100,
    ) -> list[Relationship]:
        stmt = select(RelationshipORM).where(
            RelationshipORM.from_entity_id == from_entity_id,
            RelationshipORM.is_active.is_(True),
        )
        if rel_type:
            stmt = stmt.where(RelationshipORM.type == rel_type.value)
        result = await self._session.execute(stmt.limit(limit))
        return [_orm_to_domain(r) for r in result.scalars()]

    async def get_inbound(
        self,
        to_entity_id: UUID,
        rel_type: RelationshipType | None = None,
        limit: int = 100,
    ) -> list[Relationship]:
        stmt = select(RelationshipORM).where(
            RelationshipORM.to_entity_id == to_entity_id,
            RelationshipORM.is_active.is_(True),
        )
        if rel_type:
            stmt = stmt.where(RelationshipORM.type == rel_type.value)
        result = await self._session.execute(stmt.limit(limit))
        return [_orm_to_domain(r) for r in result.scalars()]

    async def list_active(self, offset: int = 0, limit: int = 50) -> list[Relationship]:
        result = await self._session.execute(
            select(RelationshipORM)
            .where(RelationshipORM.is_active.is_(True))
            .offset(offset)
            .limit(limit)
        )
        return [_orm_to_domain(r) for r in result.scalars()]

    async def soft_delete(self, rel_id: UUID, changed_by: str) -> None:
        result = await self._session.execute(
            select(RelationshipORM).where(RelationshipORM.id == rel_id)
        )
        row = result.scalar_one()
        row.is_active = False
        row.updated_at = datetime.now(timezone.utc)
        await self._session.flush()

    async def soft_delete_by_entity(self, entity_id: UUID, changed_by: str) -> int:
        result = await self._session.execute(
            select(RelationshipORM).where(
                or_(
                    RelationshipORM.from_entity_id == entity_id,
                    RelationshipORM.to_entity_id == entity_id,
                ),
                RelationshipORM.is_active.is_(True),
            )
        )
        rows = result.scalars().all()
        now = datetime.now(timezone.utc)
        for row in rows:
            row.is_active = False
            row.updated_at = now
        await self._session.flush()
        return len(rows)

    async def update_confidence(
        self, rel_id: UUID, confidence: float, changed_by: str
    ) -> Relationship:
        result = await self._session.execute(
            select(RelationshipORM).where(RelationshipORM.id == rel_id)
        )
        row = result.scalar_one()
        row.confidence = confidence
        row.updated_at = datetime.now(timezone.utc)
        await self._session.flush()
        return _orm_to_domain(row)
