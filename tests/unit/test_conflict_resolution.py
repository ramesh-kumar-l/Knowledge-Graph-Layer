"""Unit tests for ConflictResolutionService — DISPUTED → VERIFIED/UNVERIFIED transitions."""
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.domain import Entity, EntityType, VerificationState
from src.services.conflict_resolution_service import (
    ConflictResolutionService,
    ResolutionDecision,
    ConflictResolutionError,
)


# ── helpers ────────────────────────────────────────────────────────────────────

def _entity(state: VerificationState = VerificationState.DISPUTED) -> Entity:
    return Entity(
        type=EntityType.PERSON,
        name="TestEntity",
        confidence=0.5,
        verification_state=state,
        version=2,
    )


def _make_svc(entity_repo=None, evidence_repo=None, version_svc=None, trust_svc=None):
    return ConflictResolutionService(
        entity_repo=entity_repo or AsyncMock(),
        evidence_repo=evidence_repo or AsyncMock(),
        version_svc=version_svc or AsyncMock(),
        trust_svc=trust_svc or AsyncMock(),
    )


# ── tests ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_resolve_entity_not_found_raises():
    e_repo = AsyncMock()
    e_repo.get_by_id.return_value = None
    svc = _make_svc(entity_repo=e_repo)
    with pytest.raises(ConflictResolutionError, match="not found"):
        await svc.resolve(uuid4(), ResolutionDecision.ACCEPT)


@pytest.mark.asyncio
async def test_resolve_non_disputed_entity_raises():
    e_repo = AsyncMock()
    e_repo.get_by_id.return_value = _entity(VerificationState.VERIFIED)
    svc = _make_svc(entity_repo=e_repo)
    with pytest.raises(ConflictResolutionError, match="not DISPUTED"):
        await svc.resolve(uuid4(), ResolutionDecision.ACCEPT)


@pytest.mark.asyncio
async def test_resolve_accept_transitions_to_verified():
    entity = _entity(VerificationState.DISPUTED)
    verified = entity.model_copy(update={"verification_state": VerificationState.VERIFIED})

    e_repo = AsyncMock()
    e_repo.get_by_id.return_value = entity
    e_repo.update.return_value = verified

    v_svc = AsyncMock()
    ts_svc = AsyncMock()

    svc = _make_svc(entity_repo=e_repo, version_svc=v_svc, trust_svc=ts_svc)
    result = await svc.resolve(entity.id, ResolutionDecision.ACCEPT, resolved_by="alice")

    assert result.verification_state == VerificationState.VERIFIED
    v_svc.create_version_before_write.assert_called_once()
    ts_svc.compute_and_persist.assert_called_once()

    # Verify correct change_reason
    call_kwargs = e_repo.update.call_args.args[1]
    assert "accept" in call_kwargs.change_reason
    assert call_kwargs.changed_by == "alice"


@pytest.mark.asyncio
async def test_resolve_reject_transitions_to_unverified():
    entity = _entity(VerificationState.DISPUTED)
    unverified = entity.model_copy(update={"verification_state": VerificationState.UNVERIFIED})

    e_repo = AsyncMock()
    e_repo.get_by_id.return_value = entity
    e_repo.update.return_value = unverified

    svc = _make_svc(entity_repo=e_repo)
    result = await svc.resolve(entity.id, ResolutionDecision.REJECT, resolved_by="bob")

    assert result.verification_state == VerificationState.UNVERIFIED

    call_kwargs = e_repo.update.call_args.args[1]
    assert "reject" in call_kwargs.change_reason
    assert call_kwargs.changed_by == "bob"


@pytest.mark.asyncio
async def test_resolve_version_log_written_before_update():
    """Version log must be created before the entity update (DEC-0006)."""
    entity = _entity(VerificationState.DISPUTED)
    updated = entity.model_copy(update={"verification_state": VerificationState.VERIFIED})

    call_order = []
    e_repo = AsyncMock()
    e_repo.get_by_id.return_value = entity
    e_repo.update.side_effect = lambda *a, **kw: (
        call_order.append("update") or updated
    )

    v_svc = AsyncMock()
    v_svc.create_version_before_write.side_effect = lambda **kw: (
        call_order.append("version") or None
    )

    svc = _make_svc(entity_repo=e_repo, version_svc=v_svc)
    await svc.resolve(entity.id, ResolutionDecision.ACCEPT)

    assert call_order == ["version", "update"]


@pytest.mark.asyncio
async def test_resolve_trust_recomputed_after_state_change():
    entity = _entity(VerificationState.DISPUTED)
    verified = entity.model_copy(update={"verification_state": VerificationState.VERIFIED})

    e_repo = AsyncMock()
    e_repo.get_by_id.return_value = entity
    e_repo.update.return_value = verified

    ts_svc = AsyncMock()
    svc = _make_svc(entity_repo=e_repo, trust_svc=ts_svc)
    await svc.resolve(entity.id, ResolutionDecision.ACCEPT)

    ts_svc.compute_and_persist.assert_called_once()
    kwargs = ts_svc.compute_and_persist.call_args.kwargs
    assert kwargs["subject_id"] == verified.id
    assert kwargs["verification_state"] == VerificationState.VERIFIED


@pytest.mark.asyncio
async def test_resolve_with_custom_reason_included_in_change_reason():
    entity = _entity(VerificationState.DISPUTED)
    updated = entity.model_copy(update={"verification_state": VerificationState.VERIFIED})

    e_repo = AsyncMock()
    e_repo.get_by_id.return_value = entity
    e_repo.update.return_value = updated

    svc = _make_svc(entity_repo=e_repo)
    await svc.resolve(entity.id, ResolutionDecision.ACCEPT, reason="manual review")

    kwargs = e_repo.update.call_args.args[1]
    assert "manual review" in kwargs.change_reason


@pytest.mark.asyncio
async def test_resolve_unverified_entity_raises():
    """Only DISPUTED entities can be resolved — UNVERIFIED is not a conflict state."""
    e_repo = AsyncMock()
    e_repo.get_by_id.return_value = _entity(VerificationState.UNVERIFIED)
    svc = _make_svc(entity_repo=e_repo)
    with pytest.raises(ConflictResolutionError):
        await svc.resolve(uuid4(), ResolutionDecision.REJECT)
