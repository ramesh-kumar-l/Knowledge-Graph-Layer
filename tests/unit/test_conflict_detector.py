"""Unit tests for ConflictDetector — mocked repositories."""
import uuid
from unittest.mock import AsyncMock

import pytest

from src.domain.enums import EntityType, VerificationState, SubjectType, EvidenceSourceType
from src.domain.entity import Entity
from src.domain.evidence import Evidence
from src.ingestion.conflict_detector import ConflictDetector


def _make_entity(verification_state=VerificationState.UNVERIFIED) -> Entity:
    return Entity(
        id=uuid.uuid4(),
        type=EntityType.TASK,
        name="Fix Auth Bug",
        verification_state=verification_state,
    )


def _make_evidence(subject_id: uuid.UUID, metadata: dict) -> Evidence:
    return Evidence(
        subject_type=SubjectType.ENTITY,
        subject_id=subject_id,
        source_type=EvidenceSourceType.MEMORY,
        source_id=str(uuid.uuid4()),
        content="evidence content",
        confidence=0.8,
        extractor_id="test",
        metadata=metadata,
    )


@pytest.fixture
def mock_evidence_repo():
    repo = AsyncMock()
    repo.get_for_subject = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def mock_entity_repo():
    repo = AsyncMock()
    repo.update = AsyncMock()
    return repo


@pytest.fixture
def mock_version_svc():
    svc = AsyncMock()
    svc.create_version_before_write = AsyncMock()
    return svc


@pytest.fixture
def detector(mock_evidence_repo, mock_entity_repo, mock_version_svc):
    return ConflictDetector(mock_evidence_repo, mock_entity_repo, mock_version_svc)


class TestConflictDetector:
    async def test_no_existing_evidence_returns_empty(self, detector, mock_evidence_repo):
        entity = _make_entity()
        mock_evidence_repo.get_for_subject.return_value = []

        result = await detector.detect_and_flag(entity, {"status": "DONE"})

        assert result == []

    async def test_no_conflict_when_attributes_agree(self, detector, mock_evidence_repo, mock_entity_repo):
        entity = _make_entity()
        ev = _make_evidence(entity.id, {"status": "TODO"})
        mock_evidence_repo.get_for_subject.return_value = [ev]

        result = await detector.detect_and_flag(entity, {"status": "TODO"})

        assert result == []
        mock_entity_repo.update.assert_not_called()

    async def test_conflict_detected_on_status_mismatch(self, detector, mock_evidence_repo, mock_entity_repo, mock_version_svc):
        entity = _make_entity()
        ev = _make_evidence(entity.id, {"status": "IN_PROGRESS"})
        mock_evidence_repo.get_for_subject.return_value = [ev]
        mock_entity_repo.update.return_value = entity

        result = await detector.detect_and_flag(entity, {"status": "DONE"})

        assert len(result) == 1
        assert result[0].attribute == "status"
        assert result[0].entity_id == entity.id

    async def test_conflict_flags_entity_disputed(self, detector, mock_evidence_repo, mock_entity_repo, mock_version_svc):
        entity = _make_entity()
        ev = _make_evidence(entity.id, {"status": "IN_PROGRESS"})
        mock_evidence_repo.get_for_subject.return_value = [ev]
        mock_entity_repo.update.return_value = entity

        await detector.detect_and_flag(entity, {"status": "DONE"})

        mock_entity_repo.update.assert_called_once()
        cmd = mock_entity_repo.update.call_args[0][1]
        assert cmd.verification_state == VerificationState.DISPUTED

    async def test_already_disputed_entity_not_re_updated(self, detector, mock_evidence_repo, mock_entity_repo):
        entity = _make_entity(verification_state=VerificationState.DISPUTED)
        ev = _make_evidence(entity.id, {"status": "IN_PROGRESS"})
        mock_evidence_repo.get_for_subject.return_value = [ev]

        await detector.detect_and_flag(entity, {"status": "DONE"})

        mock_entity_repo.update.assert_not_called()

    async def test_non_conflictable_attribute_ignored(self, detector, mock_evidence_repo, mock_entity_repo):
        entity = _make_entity()
        ev = _make_evidence(entity.id, {"description": "old desc"})
        mock_evidence_repo.get_for_subject.return_value = [ev]

        result = await detector.detect_and_flag(entity, {"description": "new desc"})

        assert result == []
        mock_entity_repo.update.assert_not_called()

    async def test_multiple_conflicts_all_returned(self, detector, mock_evidence_repo, mock_entity_repo, mock_version_svc):
        entity = _make_entity()
        ev = _make_evidence(entity.id, {"status": "IN_PROGRESS", "priority": "LOW"})
        mock_evidence_repo.get_for_subject.return_value = [ev]
        mock_entity_repo.update.return_value = entity

        result = await detector.detect_and_flag(
            entity, {"status": "DONE", "priority": "HIGH"}
        )

        attributes = {c.attribute for c in result}
        assert "status" in attributes
        assert "priority" in attributes
