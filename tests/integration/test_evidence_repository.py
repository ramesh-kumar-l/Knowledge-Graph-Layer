"""Integration tests for PostgresEvidenceAdapter — covers idempotency and query logic."""
import uuid

import pytest

from src.domain import CreateEvidenceCommand, SubjectType, EvidenceSourceType, VerificationState
from src.adapters.postgres.evidence_adapter import PostgresEvidenceAdapter, DuplicateEvidenceError


def _make_cmd(subject_id: uuid.UUID, source_id: str = "mem-001") -> CreateEvidenceCommand:
    return CreateEvidenceCommand(
        subject_type=SubjectType.ENTITY,
        subject_id=subject_id,
        source_type=EvidenceSourceType.MEMORY,
        source_id=source_id,
        content="Alice works at Acme Corp",
        confidence=0.85,
        extractor_id="agent-v1",
    )


class TestEvidenceIdempotency:
    async def test_create_and_retrieve(self, evidence_adapter: PostgresEvidenceAdapter):
        subject_id = uuid.uuid4()
        ev = await evidence_adapter.create(_make_cmd(subject_id))
        assert ev.subject_id == subject_id
        assert ev.confidence == 0.85
        assert ev.source_id == "mem-001"

        fetched = await evidence_adapter.get_by_id(ev.id)
        assert fetched is not None
        assert fetched.id == ev.id

    async def test_duplicate_raises_error(self, evidence_adapter: PostgresEvidenceAdapter):
        subject_id = uuid.uuid4()
        await evidence_adapter.create(_make_cmd(subject_id, source_id="mem-dup"))
        with pytest.raises(DuplicateEvidenceError):
            await evidence_adapter.create(_make_cmd(subject_id, source_id="mem-dup"))

    async def test_exists_check(self, evidence_adapter: PostgresEvidenceAdapter):
        subject_id = uuid.uuid4()
        assert not await evidence_adapter.exists(subject_id, "mem-999")
        await evidence_adapter.create(_make_cmd(subject_id, source_id="mem-999"))
        assert await evidence_adapter.exists(subject_id, "mem-999")

    async def test_get_for_subject_returns_all(self, evidence_adapter: PostgresEvidenceAdapter):
        subject_id = uuid.uuid4()
        await evidence_adapter.create(_make_cmd(subject_id, source_id="src-a"))
        await evidence_adapter.create(_make_cmd(subject_id, source_id="src-b"))
        # Different subject — should not appear
        await evidence_adapter.create(_make_cmd(uuid.uuid4(), source_id="src-c"))

        results = await evidence_adapter.get_for_subject(SubjectType.ENTITY, subject_id)
        assert len(results) == 2

    async def test_count_disputed(self, evidence_adapter: PostgresEvidenceAdapter):
        subject_id = uuid.uuid4()
        await evidence_adapter.create(
            CreateEvidenceCommand(
                subject_type=SubjectType.ENTITY,
                subject_id=subject_id,
                source_type=EvidenceSourceType.MEMORY,
                source_id="ev-1",
                content="Alice is at Acme",
                confidence=0.8,
                extractor_id="agent-1",
                verification_state=VerificationState.DISPUTED,
            )
        )
        await evidence_adapter.create(
            CreateEvidenceCommand(
                subject_type=SubjectType.ENTITY,
                subject_id=subject_id,
                source_type=EvidenceSourceType.USER_INPUT,
                source_id="ev-2",
                content="Alice is at BetaCorp",
                confidence=0.9,
                extractor_id="user",
                verification_state=VerificationState.VERIFIED,
            )
        )
        disputed = await evidence_adapter.count_disputed(subject_id)
        assert disputed == 1
