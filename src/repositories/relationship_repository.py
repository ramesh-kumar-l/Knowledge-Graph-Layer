from abc import ABC, abstractmethod
from uuid import UUID

from src.domain import Relationship, CreateRelationshipCommand, RelationshipType


class RelationshipRepository(ABC):
    """Storage-agnostic port for Relationship persistence (DEC-0002)."""

    @abstractmethod
    async def create(self, command: CreateRelationshipCommand) -> Relationship:
        """Create and return a new Relationship with version=1."""

    @abstractmethod
    async def get_by_id(self, rel_id: UUID) -> Relationship | None:
        """Return the active relationship or None."""

    @abstractmethod
    async def get_outbound(
        self,
        from_entity_id: UUID,
        rel_type: RelationshipType | None = None,
        limit: int = 100,
    ) -> list[Relationship]:
        """All active outbound relationships from an entity."""

    @abstractmethod
    async def get_inbound(
        self,
        to_entity_id: UUID,
        rel_type: RelationshipType | None = None,
        limit: int = 100,
    ) -> list[Relationship]:
        """All active inbound relationships to an entity."""

    @abstractmethod
    async def list_active(
        self, offset: int = 0, limit: int = 50
    ) -> list[Relationship]:
        """Return paginated active relationships."""

    @abstractmethod
    async def soft_delete(self, rel_id: UUID, changed_by: str) -> None:
        """Set isActive=False. Triggered directly or by entity cascade."""

    @abstractmethod
    async def soft_delete_by_entity(
        self, entity_id: UUID, changed_by: str
    ) -> int:
        """Cascade soft-delete all relationships attached to entity.
        Returns count of affected rows."""

    @abstractmethod
    async def update_confidence(
        self, rel_id: UUID, confidence: float, changed_by: str
    ) -> Relationship:
        """Update confidence score after trust recomputation."""
