"""Unit tests for TrustScore formula (14-trust-model.md).

No database required — tests pure domain logic.
"""
import pytest

from src.domain.trust_score import (
    TrustScoreComponents, compute_trust_score,
    WEIGHT_EVIDENCE, WEIGHT_FRESHNESS, WEIGHT_VERIFICATION, WEIGHT_CONFLICT,
    VERIFICATION_BONUS_VERIFIED,
)


def make_components(
    evidence_weight=0.8,
    freshness_decay=1.0,
    verification_bonus=0.0,
    conflict_penalty=0.0,
    evidence_count=1,
) -> TrustScoreComponents:
    return TrustScoreComponents(
        evidence_weight=evidence_weight,
        freshness_decay=freshness_decay,
        verification_bonus=verification_bonus,
        conflict_penalty=conflict_penalty,
        evidence_count=evidence_count,
    )


class TestComputeTrustScore:
    def test_formula_weights_sum_correctly(self):
        # evidence_weight=1, freshness=1, verification=0.2, conflict=0
        c = make_components(evidence_weight=1.0, freshness_decay=1.0, verification_bonus=0.2)
        score = compute_trust_score(c)
        expected = (1.0 * 0.50) + (1.0 * 0.20) + (0.2 * 0.20) - (0.0 * 0.10)
        assert abs(score - expected) < 1e-9

    def test_clamps_to_zero(self):
        # Maximum conflict penalty should not go below 0
        c = make_components(
            evidence_weight=0.0, freshness_decay=0.0,
            verification_bonus=0.0, conflict_penalty=1.0,
        )
        assert compute_trust_score(c) == 0.0

    def test_clamps_to_one(self):
        c = make_components(
            evidence_weight=1.0, freshness_decay=1.0,
            verification_bonus=0.2, conflict_penalty=0.0,
        )
        score = compute_trust_score(c)
        assert score <= 1.0

    def test_verified_bonus_applied(self):
        base = make_components(evidence_weight=0.5, freshness_decay=0.5)
        verified = make_components(
            evidence_weight=0.5, freshness_decay=0.5,
            verification_bonus=VERIFICATION_BONUS_VERIFIED,
        )
        assert compute_trust_score(verified) > compute_trust_score(base)

    def test_conflict_penalty_reduces_score(self):
        clean = make_components(evidence_weight=0.8, freshness_decay=1.0)
        disputed = make_components(
            evidence_weight=0.8, freshness_decay=1.0, conflict_penalty=0.5,
        )
        assert compute_trust_score(disputed) < compute_trust_score(clean)

    def test_zero_evidence_yields_zero_score(self):
        c = TrustScoreComponents(
            evidence_weight=0.0, freshness_decay=0.0,
            verification_bonus=0.0, conflict_penalty=0.0, evidence_count=0,
        )
        assert compute_trust_score(c) == 0.0

    def test_fresh_evidence_scores_higher_than_stale(self):
        fresh = make_components(evidence_weight=0.8, freshness_decay=1.0)
        stale = make_components(evidence_weight=0.8, freshness_decay=0.0)
        assert compute_trust_score(fresh) > compute_trust_score(stale)

    def test_confidence_range_is_0_to_1(self):
        for ew in [0.0, 0.3, 0.6, 1.0]:
            c = make_components(evidence_weight=ew, freshness_decay=0.5)
            score = compute_trust_score(c)
            assert 0.0 <= score <= 1.0, f"score={score} out of range for evidence_weight={ew}"

    def test_multiple_conflicts_increase_penalty(self):
        one_dispute = make_components(evidence_weight=0.8, freshness_decay=1.0, conflict_penalty=0.1)
        three_disputes = make_components(evidence_weight=0.8, freshness_decay=1.0, conflict_penalty=0.3)
        assert compute_trust_score(three_disputes) < compute_trust_score(one_dispute)
