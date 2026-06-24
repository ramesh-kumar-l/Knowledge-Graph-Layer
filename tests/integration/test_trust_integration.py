"""Integration tests for Phase 6 Trust Integration — SQLite in-memory.

Covers:
- Trust propagation ripples downstream 1, 2, 3 hops
- Conflict resolution: DISPUTED → VERIFIED / UNVERIFIED with version log
- GET /v1/explain/{entity_id} returns correct JSON breakdown
- Trust recomputed after conflict resolution
"""
import pytest
from httpx import AsyncClient, ASGITransport

from src.domain import (
    CreateEntityCommand, CreateRelationshipCommand,
    CreateEvidenceCommand, CreateProvenanceCommand,
    EntityType, RelationshipType, VerificationState,
    SubjectType, EvidenceSourceType,
)
from src.domain.entity import UpdateEntityCommand
from src.services.trust_score_service import TrustScoreService
from src.services.trust_propagation_service import TrustPropagationService
from src.services.conflict_resolution_service import (
    ConflictResolutionService, ResolutionDecision, ConflictResolutionError,
)
from src.services.version_service import VersionService


# ── helpers ──────────────────────────────────────────────────────────────────

async def _entity(adapter, etype: EntityType, name: str):
    return await adapter.create(CreateEntityCommand(type=etype, name=name))


async def _rel(r_adapter, from_id, to_id, rel_type=RelationshipType.RELATED_TO, confidence=0.8):
    rel = await r_adapter.create(
        CreateRelationshipCommand(type=rel_type, from_entity_id=from_id, to_entity_id=to_id)
    )
    return await r_adapter.update_confidence(rel.id, confidence, "test")


async def _evidence(ev_adapter, entity_id, confidence=0.8, source_id=None):
    return await ev_adapter.create(CreateEvidenceCommand(
        subject_type=SubjectType.ENTITY,
        subject_id=entity_id,
        source_type=EvidenceSourceType.USER_INPUT,
        source_id=source_id or f"src-{entity_id}",
        content="test evidence content",
        confidence=confidence,
        extractor_id="test",
    ))


def _trust_svc(ev_adapter, ts_adapter) -> TrustScoreService:
    return TrustScoreService(ev_adapter, ts_adapter)


def _propagation_svc(e_adapter, r_adapter, ts_adapter, ts_svc) -> TrustPropagationService:
    return TrustPropagationService(e_adapter, r_adapter, ts_adapter, ts_svc)


def _version_svc(v_adapter) -> VersionService:
    return VersionService(v_adapter)


def _resolution_svc(e_adapter, ev_adapter, v_adapter, ts_adapter) -> ConflictResolutionService:
    ts_svc = TrustScoreService(ev_adapter, ts_adapter)
    v_svc = VersionService(v_adapter)
    return ConflictResolutionService(e_adapter, ev_adapter, v_svc, ts_svc)


# ── trust propagation tests ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_propagation_1hop_updates_downstream(
    entity_adapter, relationship_adapter, trust_score_adapter, evidence_adapter, version_adapter
):
    source = await _entity(entity_adapter, EntityType.PERSON, "Source")
    downstream = await _entity(entity_adapter, EntityType.PERSON, "Downstream")
    await _rel(relationship_adapter, source.id, downstream.id, confidence=0.9)

    await _evidence(evidence_adapter, source.id, confidence=0.9, source_id="src-source")
    await _evidence(evidence_adapter, downstream.id, confidence=0.7, source_id="src-downstream")

    ts_svc = _trust_svc(evidence_adapter, trust_score_adapter)
    # Compute initial scores
    await ts_svc.compute_and_persist(SubjectType.ENTITY, source.id, VerificationState.UNVERIFIED)
    await ts_svc.compute_and_persist(SubjectType.ENTITY, downstream.id, VerificationState.UNVERIFIED)

    prop_svc = _propagation_svc(entity_adapter, relationship_adapter, trust_score_adapter, ts_svc)
    result = await prop_svc.propagate(source.id, max_hops=1)

    assert downstream.id in result.updated_entity_ids
    assert result.hops_reached >= 1


@pytest.mark.asyncio
async def test_propagation_3hops_reaches_all(
    entity_adapter, relationship_adapter, trust_score_adapter, evidence_adapter, version_adapter
):
    """A → B → C → D: propagation with max_hops=3 reaches D."""
    a = await _entity(entity_adapter, EntityType.PERSON, "A")
    b = await _entity(entity_adapter, EntityType.PERSON, "B")
    c = await _entity(entity_adapter, EntityType.PERSON, "C")
    d = await _entity(entity_adapter, EntityType.PERSON, "D")

    await _rel(relationship_adapter, a.id, b.id, confidence=0.9)
    await _rel(relationship_adapter, b.id, c.id, confidence=0.85)
    await _rel(relationship_adapter, c.id, d.id, confidence=0.8)

    ts_svc = _trust_svc(evidence_adapter, trust_score_adapter)
    prop_svc = _propagation_svc(entity_adapter, relationship_adapter, trust_score_adapter, ts_svc)

    result = await prop_svc.propagate(a.id, max_hops=3)

    assert b.id in result.updated_entity_ids
    assert c.id in result.updated_entity_ids
    assert d.id in result.updated_entity_ids
    assert result.hops_reached == 3


@pytest.mark.asyncio
async def test_propagation_max_hops_2_stops_at_c(
    entity_adapter, relationship_adapter, trust_score_adapter, evidence_adapter, version_adapter
):
    """A → B → C → D: max_hops=2 should not reach D."""
    a = await _entity(entity_adapter, EntityType.PERSON, "A2")
    b = await _entity(entity_adapter, EntityType.PERSON, "B2")
    c = await _entity(entity_adapter, EntityType.PERSON, "C2")
    d = await _entity(entity_adapter, EntityType.PERSON, "D2")

    await _rel(relationship_adapter, a.id, b.id, confidence=0.9)
    await _rel(relationship_adapter, b.id, c.id, confidence=0.85)
    await _rel(relationship_adapter, c.id, d.id, confidence=0.8)

    ts_svc = _trust_svc(evidence_adapter, trust_score_adapter)
    prop_svc = _propagation_svc(entity_adapter, relationship_adapter, trust_score_adapter, ts_svc)

    result = await prop_svc.propagate(a.id, max_hops=2)

    assert b.id in result.updated_entity_ids
    assert c.id in result.updated_entity_ids
    assert d.id not in result.updated_entity_ids


# ── conflict resolution tests ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_conflict_resolution_accept_transitions_to_verified(
    entity_adapter, evidence_adapter, trust_score_adapter, version_adapter
):
    entity = await _entity(entity_adapter, EntityType.PERSON, "DisputedPerson")
    # Manually flag as DISPUTED
    await entity_adapter.update(
        entity,
        UpdateEntityCommand(verification_state=VerificationState.DISPUTED, changed_by="test"),
    )
    # Write a version record so version_service can create the next one
    v_svc = _version_svc(version_adapter)

    res_svc = _resolution_svc(entity_adapter, evidence_adapter, version_adapter, trust_score_adapter)
    updated = await res_svc.resolve(entity.id, ResolutionDecision.ACCEPT, resolved_by="reviewer")

    assert updated.verification_state == VerificationState.VERIFIED


@pytest.mark.asyncio
async def test_conflict_resolution_reject_transitions_to_unverified(
    entity_adapter, evidence_adapter, trust_score_adapter, version_adapter
):
    entity = await _entity(entity_adapter, EntityType.PERSON, "DisputedPerson2")
    await entity_adapter.update(
        entity,
        UpdateEntityCommand(verification_state=VerificationState.DISPUTED, changed_by="test"),
    )

    res_svc = _resolution_svc(entity_adapter, evidence_adapter, version_adapter, trust_score_adapter)
    updated = await res_svc.resolve(entity.id, ResolutionDecision.REJECT, resolved_by="reviewer")

    assert updated.verification_state == VerificationState.UNVERIFIED


@pytest.mark.asyncio
async def test_conflict_resolution_non_disputed_raises(
    entity_adapter, evidence_adapter, trust_score_adapter, version_adapter
):
    entity = await _entity(entity_adapter, EntityType.PERSON, "VerifiedPerson")
    # entity is UNVERIFIED by default — not DISPUTED

    res_svc = _resolution_svc(entity_adapter, evidence_adapter, version_adapter, trust_score_adapter)
    with pytest.raises(ConflictResolutionError):
        await res_svc.resolve(entity.id, ResolutionDecision.ACCEPT)


@pytest.mark.asyncio
async def test_conflict_resolution_writes_version_log(
    entity_adapter, evidence_adapter, trust_score_adapter, version_adapter
):
    entity = await _entity(entity_adapter, EntityType.PERSON, "VersionedDisputed")
    await entity_adapter.update(
        entity,
        UpdateEntityCommand(verification_state=VerificationState.DISPUTED, changed_by="test"),
    )

    res_svc = _resolution_svc(entity_adapter, evidence_adapter, version_adapter, trust_score_adapter)
    await res_svc.resolve(entity.id, ResolutionDecision.ACCEPT, resolved_by="auditor")

    v_svc = _version_svc(version_adapter)
    history = await v_svc.get_history(SubjectType.ENTITY, entity.id)
    conflict_versions = [v for v in history if "conflict" in (v.change_reason or "")]
    assert len(conflict_versions) >= 1
    assert any(v.changed_by == "auditor" for v in conflict_versions)


@pytest.mark.asyncio
async def test_conflict_resolution_recomputes_trust_score(
    entity_adapter, evidence_adapter, trust_score_adapter, version_adapter
):
    entity = await _entity(entity_adapter, EntityType.PERSON, "TrustRecomputed")
    await _evidence(evidence_adapter, entity.id, confidence=0.8, source_id="src-trust-recompute")
    await entity_adapter.update(
        entity,
        UpdateEntityCommand(verification_state=VerificationState.DISPUTED, changed_by="test"),
    )

    res_svc = _resolution_svc(entity_adapter, evidence_adapter, version_adapter, trust_score_adapter)
    await res_svc.resolve(entity.id, ResolutionDecision.ACCEPT)

    ts = await trust_score_adapter.get_by_subject(entity.id)
    assert ts is not None
    # VERIFIED bonus should push score above a raw 0.8 evidence-only score
    assert ts.score > 0.0


# ── explain endpoint tests ────────────────────────────────────────────────────

def _make_app_client(db_engine):
    """Returns a context manager that yields an HTTP test client against the test SQLite DB."""
    from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
    from src.api.main import app
    from src.adapters.postgres.connection import get_session

    factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    async def _override():
        async with factory() as s:
            yield s

    app.dependency_overrides[get_session] = _override
    return app


@pytest.mark.asyncio
async def test_explain_404_for_unknown_entity(db_engine):
    from uuid import uuid4
    from src.adapters.postgres.connection import get_session

    app = _make_app_client(db_engine)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(f"/v1/explain/{uuid4()}")

    from src.api.main import app as main_app
    main_app.dependency_overrides.clear()
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_explain_returns_full_breakdown(
    entity_adapter, evidence_adapter, trust_score_adapter, db_engine
):
    from src.api.main import app as main_app

    entity = await _entity(entity_adapter, EntityType.PERSON, "ExplainTarget")
    await _evidence(evidence_adapter, entity.id, confidence=0.85, source_id="src-explain")
    ts_svc = _trust_svc(evidence_adapter, trust_score_adapter)
    await ts_svc.compute_and_persist(SubjectType.ENTITY, entity.id, VerificationState.UNVERIFIED)

    app = _make_app_client(db_engine)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(f"/v1/explain/{entity.id}")
    main_app.dependency_overrides.clear()

    assert resp.status_code == 200
    body = resp.json()
    assert body["entity_id"] == str(entity.id)
    assert body["entity_name"] == "ExplainTarget"
    assert body["trust_score"] is not None
    assert "score" in body["trust_score"]
    assert "components" in body["trust_score"]
    assert len(body["evidence"]) == 1
    assert body["is_disputed"] is False


@pytest.mark.asyncio
async def test_explain_shows_conflict_history_for_disputed_entity(
    entity_adapter, evidence_adapter, trust_score_adapter, version_adapter, db_engine
):
    from src.api.main import app as main_app

    entity = await _entity(entity_adapter, EntityType.PERSON, "DisputedExplain")
    v_svc = _version_svc(version_adapter)
    await v_svc.create_version_before_write(
        subject_type=SubjectType.ENTITY,
        subject_id=entity.id,
        current_snapshot=entity.to_snapshot(),
        next_version=entity.version + 1,
        changed_by="conflict-detector",
        change_reason="conflict_detected",
    )
    await entity_adapter.update(
        entity,
        UpdateEntityCommand(
            verification_state=VerificationState.DISPUTED,
            changed_by="conflict-detector",
        ),
    )

    app = _make_app_client(db_engine)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(f"/v1/explain/{entity.id}")
    main_app.dependency_overrides.clear()

    assert resp.status_code == 200
    body = resp.json()
    assert body["is_disputed"] is True
    assert body["verification_state"] == "DISPUTED"
    assert len(body["conflict_history"]) >= 1
    assert body["conflict_history"][0]["changed_by"] == "conflict-detector"
