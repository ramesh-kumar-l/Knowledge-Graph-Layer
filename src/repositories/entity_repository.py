from abc import ABC, abstractmethod
from uuid import UUID

from src.domain import Entity, CreateEntityCommand, UpdateEntityCommand, EntityType


class EntityRepository(ABC):
    """Storage-agnostic port for Entity persistence (DEC-0002)."""

    @abstractmethod
    async def create(self, command: CreateEntityCommand) -> Entity:
        """Create and return a new Entity with version=1."""

    @abstractmethod
    async def get_by_id(self, entity_id: UUID) -> Entity | None:
        """Return the active entity or None."""

    @abstractmethod
    async def get_by_type_and_name(
        self, entity_type: EntityType, name: str
    ) -> Entity | None:
        """Exact-match lookup for deduplication."""

    @abstractmethod
    async def list_active(
        self, offset: int = 0, limit: int = 50
    ) -> list[Entity]:
        """Return paginated active entities."""

    @abstractmethod
    async def update(
        self, entity: Entity, command: UpdateEntityCommand
    ) -> Entity:
        """Apply update, increment version, write Version record inside one transaction."""

    @abstractmethod
    async def soft_delete(self, entity_id: UUID, changed_by: str) -> None:
        """Set isActive=False; cascade to attached Relationships.
        Hard deletion is prohibited (22-graph-schema.md rule 6)."""

    @abstractmethod
    async def search_by_name(
        self,
        query: str,
        entity_type: EntityType | None = None,
        min_confidence: float = 0.5,
        limit: int = 20,
    ) -> list[Entity]:
        """Full-text search on name and aliases."""

    @abstractmethod
    async def get_by_ids(self, entity_ids: list[UUID]) -> list[Entity]:
        """Batch fetch — used by graph traversal."""

    @abstractmethod
    async def count_active(self) -> int:
        """Total count of active entities."""
