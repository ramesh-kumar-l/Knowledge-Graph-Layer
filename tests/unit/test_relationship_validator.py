"""Unit tests for RelationshipValidator — entity-type constraint enforcement."""
from uuid import uuid4

import pytest

from src.domain.enums import EntityType, RelationshipType
from src.ingestion.models import CandidateRelationship
from src.ingestion.relationship_validator import RelationshipValidator


def _candidate(
    from_type: EntityType,
    to_type: EntityType,
    rel_type: RelationshipType,
) -> CandidateRelationship:
    return CandidateRelationship(
        from_entity_id=uuid4(),
        from_entity_type=from_type,
        to_entity_id=uuid4(),
        to_entity_type=to_type,
        relationship_type=rel_type,
        confidence=0.80,
    )


class TestConstrainedRelationships:
    def test_assigned_to_valid(self):
        v = RelationshipValidator()
        c = _candidate(EntityType.TASK, EntityType.PERSON, RelationshipType.ASSIGNED_TO)
        valid, violation = v.validate(c)
        assert valid is True
        assert violation is None

    def test_assigned_to_wrong_from_type(self):
        v = RelationshipValidator()
        c = _candidate(EntityType.PERSON, EntityType.PERSON, RelationshipType.ASSIGNED_TO)
        valid, violation = v.validate(c)
        assert valid is False
        assert violation is not None
        assert violation.relationship_type == RelationshipType.ASSIGNED_TO.value

    def test_assigned_to_wrong_to_type(self):
        v = RelationshipValidator()
        c = _candidate(EntityType.TASK, EntityType.PROJECT, RelationshipType.ASSIGNED_TO)
        valid, violation = v.validate(c)
        assert valid is False

    def test_authored_by_document_valid(self):
        v = RelationshipValidator()
        c = _candidate(EntityType.DOCUMENT, EntityType.PERSON, RelationshipType.AUTHORED_BY)
        valid, _ = v.validate(c)
        assert valid is True

    def test_authored_by_artifact_valid(self):
        v = RelationshipValidator()
        c = _candidate(EntityType.ARTIFACT, EntityType.PERSON, RelationshipType.AUTHORED_BY)
        valid, _ = v.validate(c)
        assert valid is True

    def test_authored_by_wrong_to_type(self):
        v = RelationshipValidator()
        c = _candidate(EntityType.DOCUMENT, EntityType.PROJECT, RelationshipType.AUTHORED_BY)
        valid, _ = v.validate(c)
        assert valid is False

    def test_works_toward_task_valid(self):
        v = RelationshipValidator()
        c = _candidate(EntityType.TASK, EntityType.GOAL, RelationshipType.WORKS_TOWARD)
        valid, _ = v.validate(c)
        assert valid is True

    def test_works_toward_project_valid(self):
        v = RelationshipValidator()
        c = _candidate(EntityType.PROJECT, EntityType.GOAL, RelationshipType.WORKS_TOWARD)
        valid, _ = v.validate(c)
        assert valid is True

    def test_works_toward_wrong_to(self):
        v = RelationshipValidator()
        c = _candidate(EntityType.TASK, EntityType.PERSON, RelationshipType.WORKS_TOWARD)
        valid, _ = v.validate(c)
        assert valid is False

    def test_reports_to_person_valid(self):
        v = RelationshipValidator()
        c = _candidate(EntityType.PERSON, EntityType.PERSON, RelationshipType.REPORTS_TO)
        valid, _ = v.validate(c)
        assert valid is True

    def test_reports_to_wrong_from(self):
        v = RelationshipValidator()
        c = _candidate(EntityType.PROJECT, EntityType.PERSON, RelationshipType.REPORTS_TO)
        valid, _ = v.validate(c)
        assert valid is False

    def test_member_of_project_valid(self):
        v = RelationshipValidator()
        c = _candidate(EntityType.PERSON, EntityType.PROJECT, RelationshipType.MEMBER_OF)
        valid, _ = v.validate(c)
        assert valid is True

    def test_member_of_organization_valid(self):
        v = RelationshipValidator()
        c = _candidate(EntityType.PERSON, EntityType.ORGANIZATION, RelationshipType.MEMBER_OF)
        valid, _ = v.validate(c)
        assert valid is True

    def test_member_of_wrong_from(self):
        v = RelationshipValidator()
        c = _candidate(EntityType.PROJECT, EntityType.ORGANIZATION, RelationshipType.MEMBER_OF)
        valid, _ = v.validate(c)
        assert valid is False

    def test_depends_on_artifact_artifact_valid(self):
        v = RelationshipValidator()
        c = _candidate(EntityType.ARTIFACT, EntityType.ARTIFACT, RelationshipType.DEPENDS_ON)
        valid, _ = v.validate(c)
        assert valid is True

    def test_depends_on_wrong_from(self):
        v = RelationshipValidator()
        c = _candidate(EntityType.PERSON, EntityType.ARTIFACT, RelationshipType.DEPENDS_ON)
        valid, _ = v.validate(c)
        assert valid is False


class TestSameTypeConstraint:
    def test_is_same_as_same_type_valid(self):
        v = RelationshipValidator()
        c = _candidate(EntityType.PERSON, EntityType.PERSON, RelationshipType.IS_SAME_AS)
        valid, _ = v.validate(c)
        assert valid is True

    def test_is_same_as_different_types_invalid(self):
        v = RelationshipValidator()
        c = _candidate(EntityType.PERSON, EntityType.PROJECT, RelationshipType.IS_SAME_AS)
        valid, violation = v.validate(c)
        assert valid is False
        assert violation is not None

    def test_is_same_as_product_product_valid(self):
        v = RelationshipValidator()
        c = _candidate(EntityType.PRODUCT, EntityType.PRODUCT, RelationshipType.IS_SAME_AS)
        valid, _ = v.validate(c)
        assert valid is True


class TestUnconstrainedRelationships:
    def test_related_to_any_types_valid(self):
        v = RelationshipValidator()
        c = _candidate(EntityType.CONCEPT, EntityType.PRODUCT, RelationshipType.RELATED_TO)
        valid, violation = v.validate(c)
        assert valid is True
        assert violation is None

    def test_blocks_any_types_valid(self):
        v = RelationshipValidator()
        c = _candidate(EntityType.TASK, EntityType.TASK, RelationshipType.BLOCKS)
        valid, _ = v.validate(c)
        assert valid is True

    def test_owns_any_types_valid(self):
        v = RelationshipValidator()
        c = _candidate(EntityType.ORGANIZATION, EntityType.DOCUMENT, RelationshipType.OWNS)
        valid, _ = v.validate(c)
        assert valid is True


class TestViolationEventFields:
    def test_violation_event_has_all_fields(self):
        v = RelationshipValidator()
        c = _candidate(EntityType.PERSON, EntityType.PERSON, RelationshipType.ASSIGNED_TO)
        valid, violation = v.validate(c)
        assert valid is False
        assert violation.event_type == "RelationshipConstraintViolated"
        assert violation.from_entity_id == c.from_entity_id
        assert violation.to_entity_id == c.to_entity_id
        assert violation.relationship_type == RelationshipType.ASSIGNED_TO.value
        assert violation.from_entity_type == EntityType.PERSON.value
