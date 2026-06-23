from abc import ABC, abstractmethod
from uuid import UUID

from src.domain import Evidence, CreateEvidenceCommand, SubjectType


class EvidenceRepository(ABC):
    """Storage-agnostic port for Evidence persistence (DEC-0002).

    Evidence is immutable after creation. The unique constraint on
    (subject_id, source_id) enforces idempotent ingestion.
    """

    @abstractmethod
    async def create(self, command: CreateEvidenceCommand) -> Evidence:
        """Create evidence. Raises DuplicateEvidenceError if (subject_id, source_id) exists."""

    @abstractmethod
    async def get_by_id(self, evidence_id: UUID) -> Evidence | None:
        """Return evidence record or None."""

    @abstractmethod
    async def get_for_subject(
        self,
        subject_type: SubjectType,
        subject_id: UUID,
    ) -> list[Evidence]:
        """Return all evidence attached to an entity or relationship."""

    @abstractmethod
    async def exists(self, subject_id: UUID, source_id: str) -> bool:
        """Check idempotency — returns True if evidence already ingested."""

    @abstractmethod
    async def count_disputed(self, subject_id: UUID) -> int:
        """Count DISPUTED evidence records for conflict penalty calculation."""

    @abstractmethod
    async def exists_by_source_id(self, source_id: str) -> bool:
        """Global idempotency check — True if any evidence with this source_id exists."""
