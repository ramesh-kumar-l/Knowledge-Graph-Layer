"""Unit tests for RelationshipExtractor — pattern matching and precision benchmark."""
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from src.domain.enums import EntityType, RelationshipType
from src.ingestion.models import MemoryRecord, ResolvedEntityRef
from src.ingestion.relationship_extractor import RelationshipExtractor


def _record(content: str, metadata: dict | None = None) -> MemoryRecord:
    return MemoryRecord(
        id=str(uuid4()),
        content=content,
        timestamp=datetime.now(timezone.utc),
        metadata=metadata or {},
    )


def _ref(name: str, entity_type: EntityType) -> ResolvedEntityRef:
    return ResolvedEntityRef(entity_id=uuid4(), entity_type=entity_type, name=name)


# ── basic extraction tests ────────────────────────────────────────────────────

class TestExtractFromContent:
    def test_assigned_to_pattern(self):
        extractor = RelationshipExtractor()
        task = _ref("Fix Login Bug", EntityType.TASK)
        person = _ref("Alice Chen", EntityType.PERSON)
        record = _record("Fix Login Bug assigned to Alice Chen")

        result = extractor.extract(record, [task, person])

        assert len(result) == 1
        assert result[0].relationship_type == RelationshipType.ASSIGNED_TO
        assert result[0].from_entity_id == task.entity_id
        assert result[0].to_entity_id == person.entity_id

    def test_reports_to_pattern(self):
        extractor = RelationshipExtractor()
        alice = _ref("Alice Chen", EntityType.PERSON)
        bob = _ref("Bob Smith", EntityType.PERSON)
        record = _record("Alice Chen reports to Bob Smith")

        result = extractor.extract(record, [alice, bob])

        assert len(result) == 1
        assert result[0].relationship_type == RelationshipType.REPORTS_TO

    def test_authored_by_pattern(self):
        extractor = RelationshipExtractor()
        doc = _ref("Technical Spec", EntityType.DOCUMENT)
        person = _ref("Alice Chen", EntityType.PERSON)
        record = _record("Technical Spec authored by Alice Chen")

        result = extractor.extract(record, [doc, person])

        assert len(result) == 1
        assert result[0].relationship_type == RelationshipType.AUTHORED_BY

    def test_depends_on_pattern(self):
        extractor = RelationshipExtractor()
        svc = _ref("Backend Service", EntityType.PRODUCT)
        lib = _ref("Auth Library", EntityType.ARTIFACT)
        record = _record("Backend Service depends on Auth Library")

        result = extractor.extract(record, [svc, lib])

        assert len(result) == 1
        assert result[0].relationship_type == RelationshipType.DEPENDS_ON

    def test_fewer_than_two_entities_returns_empty(self):
        extractor = RelationshipExtractor()
        entity = _ref("Alice Chen", EntityType.PERSON)
        record = _record("Alice Chen is working")

        result = extractor.extract(record, [entity])

        assert result == []

    def test_no_pattern_match_returns_empty(self):
        extractor = RelationshipExtractor()
        alice = _ref("Alice Chen", EntityType.PERSON)
        bob = _ref("Bob Smith", EntityType.PERSON)
        record = _record("Alice Chen and Bob Smith were both present")

        result = extractor.extract(record, [alice, bob])

        assert result == []

    def test_duplicate_suppressed_within_record(self):
        extractor = RelationshipExtractor()
        task = _ref("Fix Login Bug", EntityType.TASK)
        person = _ref("Alice Chen", EntityType.PERSON)
        # Same relationship mentioned twice in two sentences
        record = _record(
            "Fix Login Bug assigned to Alice Chen. Fix Login Bug assigned to Alice Chen."
        )

        result = extractor.extract(record, [task, person])

        assert len(result) == 1

    def test_confidence_range(self):
        extractor = RelationshipExtractor()
        task = _ref("Fix Bug", EntityType.TASK)
        person = _ref("Alice Chen", EntityType.PERSON)
        record = _record("Fix Bug assigned to Alice Chen")

        result = extractor.extract(record, [task, person])

        assert len(result) == 1
        assert 0.0 < result[0].confidence <= 1.0

    def test_self_loop_not_extracted(self):
        extractor = RelationshipExtractor()
        entity = _ref("Alice Chen", EntityType.PERSON)
        # Only one entity → can't form a relationship
        record = _record("Alice Chen reports to Alice Chen")

        result = extractor.extract(record, [entity])

        assert result == []


class TestExtractFromMetadata:
    def test_metadata_relationship_extracted(self):
        extractor = RelationshipExtractor()
        task = _ref("Fix Bug", EntityType.TASK)
        person = _ref("Alice Chen", EntityType.PERSON)
        metadata = {
            "relationships": [
                {"from": "Fix Bug", "to": "Alice Chen", "type": "ASSIGNED_TO", "confidence": 0.95}
            ]
        }
        record = _record("Some content", metadata=metadata)

        result = extractor.extract(record, [task, person])

        assert len(result) == 1
        assert result[0].relationship_type == RelationshipType.ASSIGNED_TO
        assert result[0].confidence == 0.95
        assert result[0].extraction_reason == "metadata"

    def test_metadata_unknown_type_skipped(self):
        extractor = RelationshipExtractor()
        task = _ref("Fix Bug", EntityType.TASK)
        person = _ref("Alice Chen", EntityType.PERSON)
        metadata = {
            "relationships": [
                {"from": "Fix Bug", "to": "Alice Chen", "type": "NOT_A_REAL_TYPE"}
            ]
        }
        record = _record("content", metadata=metadata)

        result = extractor.extract(record, [task, person])

        assert result == []

    def test_metadata_unknown_entity_name_skipped(self):
        extractor = RelationshipExtractor()
        task = _ref("Fix Bug", EntityType.TASK)
        person = _ref("Alice Chen", EntityType.PERSON)
        metadata = {
            "relationships": [
                {"from": "Unknown Entity", "to": "Alice Chen", "type": "ASSIGNED_TO"}
            ]
        }
        record = _record("content", metadata=metadata)

        result = extractor.extract(record, [task, person])

        assert result == []

    def test_metadata_deduped_against_content(self):
        extractor = RelationshipExtractor()
        task = _ref("Fix Bug", EntityType.TASK)
        person = _ref("Alice Chen", EntityType.PERSON)
        metadata = {
            "relationships": [
                {"from": "Fix Bug", "to": "Alice Chen", "type": "ASSIGNED_TO"}
            ]
        }
        # Same relationship also in content — should appear only once
        record = _record("Fix Bug assigned to Alice Chen", metadata=metadata)

        result = extractor.extract(record, [task, person])

        assert len(result) == 1

    def test_metadata_confidence_capped_at_095(self):
        extractor = RelationshipExtractor()
        task = _ref("Fix Bug", EntityType.TASK)
        person = _ref("Alice Chen", EntityType.PERSON)
        metadata = {
            "relationships": [
                {"from": "Fix Bug", "to": "Alice Chen", "type": "ASSIGNED_TO", "confidence": 1.5}
            ]
        }
        record = _record("content", metadata=metadata)

        result = extractor.extract(record, [task, person])

        assert result[0].confidence == 0.95


# ── precision benchmark ───────────────────────────────────────────────────────

ET = EntityType
RT = RelationshipType

_BENCHMARK: list[tuple[str, str, str, EntityType, EntityType, RelationshipType]] = [
    ("Fix Login Bug assigned to Alice Chen", "Fix Login Bug", "Alice Chen", ET.TASK, ET.PERSON, RT.ASSIGNED_TO),
    ("Backend Service depends on Auth Library", "Backend Service", "Auth Library", ET.PRODUCT, ET.ARTIFACT, RT.DEPENDS_ON),
    ("Alice Chen reports to Bob Smith", "Alice Chen", "Bob Smith", ET.PERSON, ET.PERSON, RT.REPORTS_TO),
    ("Mobile App part of Core Platform", "Mobile App", "Core Platform", ET.PRODUCT, ET.PRODUCT, RT.PART_OF),
    ("Design System contributes to User Experience", "Design System", "User Experience", ET.CONCEPT, ET.CONCEPT, RT.CONTRIBUTES_TO),
    ("Alice Chen member of Engineering Team", "Alice Chen", "Engineering Team", ET.PERSON, ET.ORGANIZATION, RT.MEMBER_OF),
    ("Auth Service integrates with OAuth Provider", "Auth Service", "OAuth Provider", ET.PRODUCT, ET.PRODUCT, RT.INTEGRATES_WITH),
    ("Technical Spec authored by Alice Chen", "Technical Spec", "Alice Chen", ET.DOCUMENT, ET.PERSON, RT.AUTHORED_BY),
    ("Build Pipeline uses Docker Container", "Build Pipeline", "Docker Container", ET.PROJECT, ET.ARTIFACT, RT.USES),
    ("Feature Release blocks Backend Deploy", "Feature Release", "Backend Deploy", ET.TASK, ET.TASK, RT.BLOCKS),
    ("API Gateway requires Auth Token", "API Gateway", "Auth Token", ET.PRODUCT, ET.ARTIFACT, RT.REQUIRES),
    ("Design Doc created by Bob Smith", "Design Doc", "Bob Smith", ET.DOCUMENT, ET.PERSON, RT.CREATED_BY),
    ("New SDK derived from Legacy Framework", "New SDK", "Legacy Framework", ET.PRODUCT, ET.ARTIFACT, RT.DERIVED_FROM),
    ("API Docs references REST Spec", "API Docs", "REST Spec", ET.DOCUMENT, ET.DOCUMENT, RT.REFERENCES),
    ("Project Alpha works toward Revenue Goal", "Project Alpha", "Revenue Goal", ET.PROJECT, ET.GOAL, RT.WORKS_TOWARD),
    ("Database Refactor enables Performance Boost", "Database Refactor", "Performance Boost", ET.TASK, ET.GOAL, RT.ENABLES),
    ("Alice Chen collaborates on Backend Project", "Alice Chen", "Backend Project", ET.PERSON, ET.PROJECT, RT.COLLABORATES_ON),
    ("Marketing Team owns Brand Guidelines", "Marketing Team", "Brand Guidelines", ET.ORGANIZATION, ET.DOCUMENT, RT.OWNS),
    ("Frontend App related to Backend Service", "Frontend App", "Backend Service", ET.PRODUCT, ET.PRODUCT, RT.RELATED_TO),
    ("Planning Phase preceded by Bootstrap Phase", "Planning Phase", "Bootstrap Phase", ET.EVENT, ET.EVENT, RT.PRECEDED_BY),
    ("Phase Two followed by Phase Three", "Phase Two", "Phase Three", ET.PROJECT, ET.PROJECT, RT.FOLLOWED_BY),
    ("Sprint Review contains Status Update", "Sprint Review", "Status Update", ET.EVENT, ET.TASK, RT.CONTAINS),
    ("Sub Goal child of Main Goal", "Sub Goal", "Main Goal", ET.GOAL, ET.GOAL, RT.CHILD_OF),
    ("Main Goal parent of Sub Goal", "Main Goal", "Sub Goal", ET.GOAL, ET.GOAL, RT.PARENT_OF),
    ("Team Meeting scheduled on Launch Day", "Team Meeting", "Launch Day", ET.EVENT, ET.EVENT, RT.SCHEDULED_ON),
    ("React Library similar to Vue Framework", "React Library", "Vue Framework", ET.PRODUCT, ET.PRODUCT, RT.SIMILAR_TO),
    ("Old Design contradicts New Design", "Old Design", "New Design", ET.DOCUMENT, ET.DOCUMENT, RT.CONTRADICTS),
    ("Feature X is alias of Feature Y", "Feature X", "Feature Y", ET.PRODUCT, ET.PRODUCT, RT.IS_ALIAS_OF),
    ("Version Two is variation of Version One", "Version Two", "Version One", ET.PRODUCT, ET.PRODUCT, RT.IS_VARIATION_OF),
    ("Backend Service maintained by Alice Chen", "Backend Service", "Alice Chen", ET.PRODUCT, ET.PERSON, RT.MAINTAINED_BY),
]


def test_precision_benchmark_30_records():
    """≥85% precision on relationship type classification across 30 fixture records."""
    extractor = RelationshipExtractor()
    correct = 0

    for content, from_name, to_name, from_type, to_type, expected_type in _BENCHMARK:
        from_ref = ResolvedEntityRef(entity_id=uuid4(), entity_type=from_type, name=from_name)
        to_ref = ResolvedEntityRef(entity_id=uuid4(), entity_type=to_type, name=to_name)
        record = _record(content)

        candidates = extractor.extract(record, [from_ref, to_ref])

        if any(c.relationship_type == expected_type for c in candidates):
            correct += 1

    precision = correct / len(_BENCHMARK)
    assert precision >= 0.85, (
        f"Precision {precision:.2%} below 85% threshold "
        f"({correct}/{len(_BENCHMARK)} correct)"
    )
