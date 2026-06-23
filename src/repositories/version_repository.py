from abc import ABC, abstractmethod
from uuid import UUID

from src.domain import Version, CreateVersionCommand, SubjectType


class VersionRepository(ABC):
    """Storage-agnostic port for Version log persistence (DEC-0002, DEC-0006).

    The version log is append-only. Past versions are never mutated.
    Write sequence (must be inside one transaction):
      1. read current state
      2. compute diff (JSON Patch)
      3. INSERT version record  ← this method
      4. UPDATE entity/relationship
    """

    @abstractmethod
    async def create(self, command: CreateVersionCommand) -> Version:
        """Append a version record. Enforces (subject_id, version) uniqueness."""

    @abstractmethod
    async def get_latest(
        self, subject_type: SubjectType, subject_id: UUID
    ) -> Version | None:
        """Return the highest-version record for a subject."""

    @abstractmethod
    async def list_for_subject(
        self,
        subject_type: SubjectType,
        subject_id: UUID,
        offset: int = 0,
        limit: int = 50,
    ) -> list[Version]:
        """Return version history in ascending order."""

    @abstractmethod
    async def get_by_version(
        self, subject_id: UUID, version: int
    ) -> Version | None:
        """Time-travel: return the snapshot at a specific version number."""
