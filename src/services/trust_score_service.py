"""TrustScore computation service.

Formula (from 14-trust-model.md):
  score = clamp(
      (evidenceWeight × 0.50) + (freshnessDecay × 0.20)
    + (verificationBonus × 0.20) - (conflictPenalty × 0.10)
  , 0.0, 1.0)
"""
import logging
from datetime import datetime, timezone
from uuid import UUID

from src.domain import TrustScore, SubjectType, VerificationState
from src.domain.enums import EVIDENCE_SOURCE_WEIGHTS
from src.domain.trust_score import (
    TrustScoreComponents, compute_trust_score,
    VERIFICATION_BONUS_VERIFIED, CONFLICT_PENALTY_PER_DISPUTE, FRESHNESS_WINDOW_DAYS,
)
from src.repositories import EvidenceRepository, TrustScoreRepository

log = logging.getLogger(__name__)


class TrustScoreService:
    def __init__(
        self,
        evidence_repo: EvidenceRepository,
        trust_repo: TrustScoreRepository,
    ) -> None:
        self._evidence = evidence_repo
        self._trust = trust_repo

    async def compute_and_persist(
        self,
        subject_type: SubjectType,
        subject_id: UUID,
        verification_state: VerificationState,
    ) -> TrustScore:
        evidence_list = await self._evidence.get_for_subject(subject_type, subject_id)
        if not evidence_list:
            components = TrustScoreComponents(
                evidence_weight=0.0,
                freshness_decay=0.0,
                verification_bonus=0.0,
                conflict_penalty=0.0,
                evidence_count=0,
            )
            score_value = 0.0
        else:
            components = self._build_components(evidence_list, verification_state)
            score_value = compute_trust_score(components)

        trust_score = TrustScore(
            subject_id=subject_id,
            score=score_value,
            components=components,
        )
        result = await self._trust.upsert(trust_score)

        log.info(
            "trust_score_computed subject=%s score=%.3f algorithm=%s",
            subject_id, result.score, result.algorithm,
        )
        return result

    def _build_components(self, evidence_list, verification_state: VerificationState) -> TrustScoreComponents:
        total_weight = 0.0
        weighted_sum = 0.0
        disputed_count = 0
        most_recent: datetime | None = None

        for ev in evidence_list:
            w = EVIDENCE_SOURCE_WEIGHTS.get(ev.source_type, 0.6)
            weighted_sum += ev.confidence * w
            total_weight += w
            if ev.verification_state == VerificationState.DISPUTED:
                disputed_count += 1
            if most_recent is None or ev.extracted_at > most_recent:
                most_recent = ev.extracted_at

        evidence_weight = weighted_sum / total_weight if total_weight > 0 else 0.0

        age_days = 0.0
        if most_recent:
            now = datetime.now(timezone.utc)
            delta = now - most_recent.replace(tzinfo=timezone.utc) if most_recent.tzinfo is None else now - most_recent
            age_days = delta.total_seconds() / 86400.0
        freshness_decay = max(0.0, 1.0 - (age_days / FRESHNESS_WINDOW_DAYS))

        verification_bonus = VERIFICATION_BONUS_VERIFIED if verification_state == VerificationState.VERIFIED else 0.0
        conflict_penalty = min(1.0, disputed_count * CONFLICT_PENALTY_PER_DISPUTE)

        return TrustScoreComponents(
            evidence_weight=evidence_weight,
            freshness_decay=freshness_decay,
            verification_bonus=verification_bonus,
            conflict_penalty=conflict_penalty,
            evidence_count=len(evidence_list),
        )
