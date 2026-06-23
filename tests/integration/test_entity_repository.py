"""Integration tests for PostgresEntityAdapter against SQLite in-memory.

These tests verify full round-trip: create, read, update, soft-delete, search.
"""
import uuid

import pytest

from src.domain import (
    CreateEntityCommand, UpdateEntityCommand,
    EntityType, VerificationState,
)
from src.adapters.postgres.entity_adapter import PostgresEntityAdapter


class TestEntityCRUD:
    async def test_create_and_get(self, entity_adapter: PostgresEntityAdapter):
        cmd = CreateEntityCommand(
            type=EntityType.PERSON,
            name="Alice",
            aliases=["ali"],
            labels=["vip"],
        )
        entity = await entity_adapter.create(cmd)
        assert entity.name == "Alice"
        assert entity.type == EntityType.PERSON
        assert entity.version == 1
        assert entity.is_active is True
        assert entity.confidence == 0.0
        assert entity.verification_state == VerificationState.UNVERIFIED

        fetched = await entity_adapter.get_by_id(entity.id)
        assert fetched is not None
        assert fetched.id == entity.id
        assert fetched.aliases == ["ali"]

    async def test_get_nonexistent_returns_none(self, entity_adapter: PostgresEntityAdapter):
        result = await entity_adapter.get_by_id(uuid.uuid4())
        assert result is None

    async def test_get_by_type_and_name(self, entity_adapter: PostgresEntityAdapter):
        cmd = CreateEntityCommand(type=EntityType.PROJECT, name="SCP KG")
        entity = await entity_adapter.create(cmd)

        found = await entity_adapter.get_by_type_and_name(EntityType.PROJECT, "SCP KG")
        assert found is not None
        assert found.id == entity.id

        not_found = await entity_adapter.get_by_type_and_name(EntityType.PERSON, "SCP KG")
        assert not_found is None

    async def test_list_active(self, entity_adapter: PostgresEntityAdapter):
        for i in range(3):
            await entity_adapter.create(
                CreateEntityCommand(type=EntityType.SKILL, name=f"Skill {i}")
            )
        entities = await entity_adapter.list_active(offset=0, limit=10)
        assert len(entities) == 3

    async def test_update_increments_version(self, entity_adapter: PostgresEntityAdapter):
        entity = await entity_adapter.create(
            CreateEntityCommand(type=EntityType.GOAL, name="Original Goal")
        )
        assert entity.version == 1

        cmd = UpdateEntityCommand(name="Updated Goal", changed_by="user-1")
        updated = await entity_adapter.update(entity, cmd)
        assert updated.version == 2
        assert updated.name == "Updated Goal"

    async def test_soft_delete_hides_entity(self, entity_adapter: PostgresEntityAdapter):
        entity = await entity_adapter.create(
            CreateEntityCommand(type=EntityType.TASK, name="Task to delete")
        )
        await entity_adapter.soft_delete(entity.id, "user-1")

        # Must not appear in normal queries
        assert await entity_adapter.get_by_id(entity.id) is None
        active_list = await entity_adapter.list_active()
        assert not any(e.id == entity.id for e in active_list)

    async def test_search_by_name(self, entity_adapter: PostgresEntityAdapter):
        await entity_adapter.create(
            CreateEntityCommand(type=EntityType.PERSON, name="Bob Smith", labels=[])
        )
        await entity_adapter.create(
            CreateEntityCommand(type=EntityType.PERSON, name="Bobby Jones", labels=[])
        )
        await entity_adapter.create(
            CreateEntityCommand(type=EntityType.ORGANIZATION, name="Bob's Org", labels=[])
        )

        results = await entity_adapter.search_by_name("Bob", min_confidence=0.0)
        assert len(results) == 3

        person_results = await entity_adapter.search_by_name(
            "Bob", entity_type=EntityType.PERSON, min_confidence=0.0
        )
        assert len(person_results) == 2

    async def test_count_active(self, entity_adapter: PostgresEntityAdapter):
        initial = await entity_adapter.count_active()
        await entity_adapter.create(
            CreateEntityCommand(type=EntityType.DOCUMENT, name="Doc 1")
        )
        await entity_adapter.create(
            CreateEntityCommand(type=EntityType.DOCUMENT, name="Doc 2")
        )
        assert await entity_adapter.count_active() == initial + 2

    async def test_get_by_ids_batch(self, entity_adapter: PostgresEntityAdapter):
        e1 = await entity_adapter.create(
            CreateEntityCommand(type=EntityType.CONCEPT, name="Concept A")
        )
        e2 = await entity_adapter.create(
            CreateEntityCommand(type=EntityType.CONCEPT, name="Concept B")
        )
        results = await entity_adapter.get_by_ids([e1.id, e2.id])
        assert len(results) == 2

    async def test_update_verification_state(self, entity_adapter: PostgresEntityAdapter):
        entity = await entity_adapter.create(
            CreateEntityCommand(type=EntityType.PERSON, name="Carol")
        )
        cmd = UpdateEntityCommand(
            verification_state=VerificationState.VERIFIED,
            changed_by="reviewer",
            change_reason="manually verified",
        )
        updated = await entity_adapter.update(entity, cmd)
        assert updated.verification_state == VerificationState.VERIFIED
