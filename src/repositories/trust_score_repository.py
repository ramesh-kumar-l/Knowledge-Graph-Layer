from abc import ABC, abstractmethod
from uuid import UUID

from src.domain import TrustScore


class TrustScoreRepository(ABC):
    """Storage-agnostic port for TrustScore persistence (DEC-0002).

    One active TrustScore per subject — unique constraint on subject_id.
    Scores are recomputed and upserted; the latest wins.
    """

    @abstractmethod
    async def upsert(self, trust_score: TrustScore) -> TrustScore:
        """Insert or replace the trust score for a subject."""

    @abstractmethod
    async def get_by_subject(self, subject_id: UUID) -> TrustScore | None:
        """Return current trust score or None."""

    @abstractmethod
    async def get_by_id(self, score_id: UUID) -> TrustScore | None:
        """Direct ID lookup."""

    @abstractmethod
    async def get_below_threshold(
        self, threshold: float, limit: int = 100
    ) -> list[TrustScore]:
        """Return subjects whose trust score is below threshold."""
