import uuid
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain import (
    Entity, CreateEntityCommand, UpdateEntityCommand, EntityType, VerificationState,
)
from src.repositories import EntityRepository
from .orm_models import EntityORM


def _orm_to_domain(row: EntityORM) -> Entity:
    return Entity(
        id=row.id,
        type=EntityType(row.type),
        name=row.name,
        aliases=row.aliases or [],
        attributes=row.attributes or {},
        confidence=row.confidence,
        verification_state=VerificationState(row.verification_state),
        source_memory_ids=row.source_memory_ids or [],
        labels=row.labels or [],
        version=row.version,
        created_at=row.created_at,
        updated_at=row.updated_at,
        is_active=row.is_active,
    )


class PostgresEntityAdapter(EntityRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, command: CreateEntityCommand) -> Entity:
        row = EntityORM(
            id=uuid.uuid4(),
            type=command.type.value,
            name=command.name,
            aliases=command.aliases,
            attributes=command.attributes,
            confidence=0.0,
            verification_state=VerificationState.UNVERIFIED.value,
            source_memory_ids=command.source_memory_ids,
            labels=command.labels,
            version=1,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            is_active=True,
        )
        self._session.add(row)
        await self._session.flush()
        return _orm_to_domain(row)

    async def get_by_id(self, entity_id: UUID) -> Entity | None:
        result = await self._session.execute(
            select(EntityORM).where(
                EntityORM.id == entity_id, EntityORM.is_active.is_(True)
            )
        )
        row = result.scalar_one_or_none()
        return _orm_to_domain(row) if row else None

    async def get_by_type_and_name(
        self, entity_type: EntityType, name: str
    ) -> Entity | None:
        result = await self._session.execute(
            select(EntityORM).where(
                EntityORM.type == entity_type.value,
                EntityORM.name == name,
                EntityORM.is_active.is_(True),
            )
        )
        row = result.scalar_one_or_none()
        return _orm_to_domain(row) if row else None

    async def list_active(self, offset: int = 0, limit: int = 50) -> list[Entity]:
        result = await self._session.execute(
            select(EntityORM)
            .where(EntityORM.is_active.is_(True))
            .offset(offset)
            .limit(limit)
        )
        return [_orm_to_domain(r) for r in result.scalars()]

    async def update(self, entity: Entity, command: UpdateEntityCommand) -> Entity:
        result = await self._session.execute(
            select(EntityORM).where(EntityORM.id == entity.id)
        )
        row = result.scalar_one()
        if command.name is not None:
            row.name = command.name
        if command.aliases is not None:
            row.aliases = command.aliases
        if command.attributes is not None:
            row.attributes = command.attributes
        if command.labels is not None:
            row.labels = command.labels
        if command.verification_state is not None:
            row.verification_state = command.verification_state.value
        row.version += 1
        row.updated_at = datetime.now(timezone.utc)
        await self._session.flush()
        return _orm_to_domain(row)

    async def soft_delete(self, entity_id: UUID, changed_by: str) -> None:
        result = await self._session.execute(
            select(EntityORM).where(EntityORM.id == entity_id)
        )
        row = result.scalar_one()
        row.is_active = False
        row.updated_at = datetime.now(timezone.utc)
        await self._session.flush()

    async def search_by_name(
        self,
        query: str,
        entity_type: EntityType | None = None,
        min_confidence: float = 0.5,
        limit: int = 20,
    ) -> list[Entity]:
        stmt = select(EntityORM).where(
            EntityORM.is_active.is_(True),
            EntityORM.confidence >= min_confidence,
            EntityORM.name.ilike(f"%{query}%"),
        )
        if entity_type:
            stmt = stmt.where(EntityORM.type == entity_type.value)
        result = await self._session.execute(stmt.limit(limit))
        return [_orm_to_domain(r) for r in result.scalars()]

    async def get_by_ids(self, entity_ids: list[UUID]) -> list[Entity]:
        if not entity_ids:
            return []
        result = await self._session.execute(
            select(EntityORM).where(
                EntityORM.id.in_(entity_ids), EntityORM.is_active.is_(True)
            )
        )
        return [_orm_to_domain(r) for r in result.scalars()]

    async def count_active(self) -> int:
        result = await self._session.execute(
            select(func.count()).where(EntityORM.is_active.is_(True))
        )
        return result.scalar_one()

    async def update_confidence(self, entity_id: UUID, confidence: float) -> None:
        result = await self._session.execute(
            select(EntityORM).where(EntityORM.id == entity_id)
        )
        row = result.scalar_one()
        row.confidence = confidence
        row.updated_at = datetime.now(timezone.utc)
        await self._session.flush()
