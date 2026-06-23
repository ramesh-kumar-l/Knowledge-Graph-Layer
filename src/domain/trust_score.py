from datetime import datetime, timezone
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TrustScoreComponents(BaseModel):
    evidence_weight: float = Field(ge=0.0, le=1.0)
    freshness_decay: float = Field(ge=0.0, le=1.0)
    verification_bonus: float = Field(ge=0.0, le=1.0)
    conflict_penalty: float = Field(ge=0.0, le=1.0)
    evidence_count: int = Field(ge=0)


class TrustScore(BaseModel):
    """Read-only. Never set directly — always computed from Evidence."""

    id: UUID = Field(default_factory=uuid4)
    subject_id: UUID
    score: float = Field(ge=0.0, le=1.0)
    components: TrustScoreComponents
    computed_at: datetime = Field(default_factory=_utcnow)
    algorithm: str = "v1"

    model_config = {"frozen": True}


# ── Formula constants ──────────────────────────────────────────────────────────

WEIGHT_EVIDENCE = 0.50
WEIGHT_FRESHNESS = 0.20
WEIGHT_VERIFICATION = 0.20
WEIGHT_CONFLICT = 0.10

VERIFICATION_BONUS_VERIFIED = 0.20
CONFLICT_PENALTY_PER_DISPUTE = 0.10
FRESHNESS_WINDOW_DAYS = 90


def compute_trust_score(components: TrustScoreComponents) -> float:
    raw = (
        components.evidence_weight * WEIGHT_EVIDENCE
        + components.freshness_decay * WEIGHT_FRESHNESS
        + components.verification_bonus * WEIGHT_VERIFICATION
        - components.conflict_penalty * WEIGHT_CONFLICT
    )
    return max(0.0, min(1.0, raw))
