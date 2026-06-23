"""Unit tests for domain model invariants (10-domain-model.md, Pydantic validation)."""
import uuid

import pytest
from pydantic import ValidationError

from src.domain import (
    Entity, CreateEntityCommand, EntityType, VerificationState,
    Relationship, CreateRelationshipCommand, RelationshipType, Direction,
    Evidence, CreateEvidenceCommand, SubjectType, EvidenceSourceType,
    Provenance, CreateProvenanceCommand,
)


class TestEntity:
    def test_entity_defaults(self):
        e = Entity(type=EntityType.PERSON, name="Alice")
        assert e.is_active is True
        assert e.version == 1
        assert e.confidence == 0.0
        assert e.verification_state == VerificationState.UNVERIFIED
        assert isinstance(e.id, uuid.UUID)

    def test_name_cannot_be_empty(self):
        with pytest.raises(ValidationError):
            Entity(type=EntityType.PERSON, name="")

    def test_confidence_bounds(self):
        with pytest.raises(ValidationError):
            Entity(type=EntityType.PERSON, name="Alice", confidence=1.5)
        with pytest.raises(ValidationError):
            Entity(type=EntityType.PERSON, name="Bob", confidence=-0.1)

    def test_to_snapshot_is_json_serializable(self):
        e = Entity(type=EntityType.PROJECT, name="KG Layer")
        snapshot = e.to_snapshot()
        assert isinstance(snapshot, dict)
        assert snapshot["name"] == "KG Layer"
        assert snapshot["type"] == "PROJECT"

    def test_entity_type_enum(self):
        for t in EntityType:
            e = Entity(type=t, name="test")
            assert e.type == t


class TestRelationship:
    def test_no_self_loop(self):
        same_id = uuid.uuid4()
        with pytest.raises(ValidationError, match="self-loop"):
            Relationship(
                type=RelationshipType.RELATED_TO,
                from_entity_id=same_id,
                to_entity_id=same_id,
            )

    def test_create_command_no_self_loop(self):
        same_id = uuid.uuid4()
        with pytest.raises(ValidationError):
            CreateRelationshipCommand(
                type=RelationshipType.DEPENDS_ON,
                from_entity_id=same_id,
                to_entity_id=same_id,
            )

    def test_directed_by_default(self):
        rel = Relationship(
            type=RelationshipType.OWNS,
            from_entity_id=uuid.uuid4(),
            to_entity_id=uuid.uuid4(),
        )
        assert rel.direction == Direction.DIRECTED

    def test_strength_bounds(self):
        with pytest.raises(ValidationError):
            Relationship(
                type=RelationshipType.OWNS,
                from_entity_id=uuid.uuid4(),
                to_entity_id=uuid.uuid4(),
                strength=1.5,
            )


class TestEvidence:
    def test_evidence_is_frozen(self):
        ev = Evidence(
            subject_type=SubjectType.ENTITY,
            subject_id=uuid.uuid4(),
            source_type=EvidenceSourceType.MEMORY,
            source_id="mem-001",
            content="Alice works at Acme Corp",
            confidence=0.85,
            extractor_id="agent-1",
        )
        with pytest.raises(Exception):
            ev.content = "modified"  # frozen model

    def test_content_max_length(self):
        with pytest.raises(ValidationError):
            Evidence(
                subject_type=SubjectType.ENTITY,
                subject_id=uuid.uuid4(),
                source_type=EvidenceSourceType.DOCUMENT,
                source_id="doc-1",
                content="x" * 4097,  # exceeds 4096 limit
                confidence=0.9,
                extractor_id="agent-1",
            )

    def test_confidence_bounds(self):
        with pytest.raises(ValidationError):
            CreateEvidenceCommand(
                subject_type=SubjectType.ENTITY,
                subject_id=uuid.uuid4(),
                source_type=EvidenceSourceType.USER_INPUT,
                source_id="user-1",
                content="valid",
                confidence=1.1,
                extractor_id="agent-1",
            )


class TestProvenance:
    def test_provenance_is_frozen(self):
        p = Provenance(
            subject_type=SubjectType.ENTITY,
            subject_id=uuid.uuid4(),
            origin="scp-memory-core",
            extraction_method="memory_extraction",
        )
        with pytest.raises(Exception):
            p.origin = "modified"
