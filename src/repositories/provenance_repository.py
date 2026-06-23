from abc import ABC, abstractmethod
from uuid import UUID

from src.domain import Provenance, CreateProvenanceCommand


class ProvenanceRepository(ABC):
    """Storage-agnostic port for Provenance persistence (DEC-0002).

    One Provenance per Entity/Relationship — enforced by unique constraint on subject_id.
    """

    @abstractmethod
    async def create(self, command: CreateProvenanceCommand) -> Provenance:
        """Create provenance. Raises if a record for subject_id already exists."""

    @abstractmethod
    async def get_by_subject(self, subject_id: UUID) -> Provenance | None:
        """Return the single provenance record for a subject or None."""

    @abstractmethod
    async def get_by_id(self, provenance_id: UUID) -> Provenance | None:
        """Direct ID lookup."""
