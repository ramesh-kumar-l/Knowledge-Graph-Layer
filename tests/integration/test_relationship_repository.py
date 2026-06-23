"""Integration tests for PostgresRelationshipAdapter."""
import uuid

import pytest

from src.domain import (
    CreateEntityCommand, CreateRelationshipCommand,
    EntityType, RelationshipType, Direction,
)
from src.adapters.postgres.entity_adapter import PostgresEntityAdapter
from src.adapters.postgres.relationship_adapter import PostgresRelationshipAdapter


@pytest.fixture
async def two_entities(entity_adapter: PostgresEntityAdapter):
    alice = await entity_adapter.create(CreateEntityCommand(type=EntityType.PERSON, name="Alice"))
    project = await entity_adapter.create(CreateEntityCommand(type=EntityType.PROJECT, name="SCP"))
    return alice, project


class TestRelationshipCRUD:
    async def test_create_and_get(
        self,
        relationship_adapter: PostgresRelationshipAdapter,
        two_entities,
    ):
        alice, project = two_entities
        cmd = CreateRelationshipCommand(
            type=RelationshipType.MEMBER_OF,
            from_entity_id=alice.id,
            to_entity_id=project.id,
        )
        rel = await relationship_adapter.create(cmd)
        assert rel.type == RelationshipType.MEMBER_OF
        assert rel.from_entity_id == alice.id
        assert rel.to_entity_id == project.id
        assert rel.version == 1
        assert rel.is_active is True
        assert rel.direction == Direction.DIRECTED

        fetched = await relationship_adapter.get_by_id(rel.id)
        assert fetched is not None
        assert fetched.id == rel.id

    async def test_self_loop_rejected_by_domain(self):
        same_id = uuid.uuid4()
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            CreateRelationshipCommand(
                type=RelationshipType.RELATED_TO,
                from_entity_id=same_id,
                to_entity_id=same_id,
            )

    async def test_get_outbound(
        self,
        relationship_adapter: PostgresRelationshipAdapter,
        entity_adapter: PostgresEntityAdapter,
    ):
        alice = await entity_adapter.create(CreateEntityCommand(type=EntityType.PERSON, name="Alice2"))
        goal = await entity_adapter.create(CreateEntityCommand(type=EntityType.GOAL, name="Goal1"))
        task = await entity_adapter.create(CreateEntityCommand(type=EntityType.TASK, name="Task1"))

        await relationship_adapter.create(
            CreateRelationshipCommand(type=RelationshipType.WORKS_TOWARD, from_entity_id=alice.id, to_entity_id=goal.id)
        )
        await relationship_adapter.create(
            CreateRelationshipCommand(type=RelationshipType.ASSIGNED_TO, from_entity_id=task.id, to_entity_id=alice.id)
        )

        outbound = await relationship_adapter.get_outbound(alice.id)
        assert len(outbound) == 1
        assert outbound[0].type == RelationshipType.WORKS_TOWARD

    async def test_get_inbound(
        self,
        relationship_adapter: PostgresRelationshipAdapter,
        entity_adapter: PostgresEntityAdapter,
    ):
        manager = await entity_adapter.create(CreateEntityCommand(type=EntityType.PERSON, name="Manager"))
        report = await entity_adapter.create(CreateEntityCommand(type=EntityType.PERSON, name="Report"))
        await relationship_adapter.create(
            CreateRelationshipCommand(type=RelationshipType.REPORTS_TO, from_entity_id=report.id, to_entity_id=manager.id)
        )
        inbound = await relationship_adapter.get_inbound(manager.id)
        assert len(inbound) == 1

    async def test_soft_delete(
        self,
        relationship_adapter: PostgresRelationshipAdapter,
        two_entities,
    ):
        alice, project = two_entities
        rel = await relationship_adapter.create(
            CreateRelationshipCommand(type=RelationshipType.OWNS, from_entity_id=alice.id, to_entity_id=project.id)
        )
        await relationship_adapter.soft_delete(rel.id, "user-1")
        assert await relationship_adapter.get_by_id(rel.id) is None

    async def test_cascade_soft_delete_by_entity(
        self,
        relationship_adapter: PostgresRelationshipAdapter,
        entity_adapter: PostgresEntityAdapter,
    ):
        src = await entity_adapter.create(CreateEntityCommand(type=EntityType.ARTIFACT, name="Artifact"))
        tgt = await entity_adapter.create(CreateEntityCommand(type=EntityType.DOCUMENT, name="Doc"))
        rel1 = await relationship_adapter.create(
            CreateRelationshipCommand(type=RelationshipType.REFERENCES, from_entity_id=src.id, to_entity_id=tgt.id)
        )
        rel2 = await relationship_adapter.create(
            CreateRelationshipCommand(type=RelationshipType.DERIVED_FROM, from_entity_id=tgt.id, to_entity_id=src.id)
        )

        count = await relationship_adapter.soft_delete_by_entity(src.id, "system")
        assert count == 2  # both rels reference src
        assert await relationship_adapter.get_by_id(rel1.id) is None
        assert await relationship_adapter.get_by_id(rel2.id) is None
