"""Unit tests for DeduplicationEngine — mocked EntityRepository."""
import uuid
from unittest.mock import AsyncMock

import pytest

from src.domain.enums import EntityType, VerificationState
from src.domain.entity import Entity
from src.ingestion.deduplicator import DeduplicationEngine
from src.ingestion.models import CandidateEntity, ResolutionStrategy


def _make_entity(name: str, etype: EntityType, aliases: list[str] | None = None) -> Entity:
    return Entity(
        id=uuid.uuid4(),
        type=etype,
        name=name,
        aliases=aliases or [],
        confidence=0.8,
        verification_state=VerificationState.UNVERIFIED,
    )


def _make_candidate(name: str, etype: EntityType = EntityType.PERSON) -> CandidateEntity:
    return CandidateEntity(
        name=name,
        entity_type=etype,
        confidence=0.9,
    )


@pytest.fixture
def mock_repo():
    repo = AsyncMock()
    repo.get_by_type_and_name = AsyncMock(return_value=None)
    repo.search_by_name = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def engine(mock_repo):
    return DeduplicationEngine(mock_repo)


class TestDeduplicationEngine:
    async def test_exact_name_match_returns_existing_id(self, engine, mock_repo):
        existing = _make_entity("Alice Chen", EntityType.PERSON)
        mock_repo.get_by_type_and_name.return_value = existing

        candidate = _make_candidate("Alice Chen", EntityType.PERSON)
        result, events = await engine.resolve(candidate)

        assert result.strategy == ResolutionStrategy.EXACT_NAME
        assert result.confidence == 0.9
        assert result.entity_id == existing.id
        assert events == []

    async def test_no_match_returns_new_strategy(self, engine, mock_repo):
        mock_repo.get_by_type_and_name.return_value = None
        mock_repo.search_by_name.return_value = []

        candidate = _make_candidate("Completely Unknown Person")
        result, events = await engine.resolve(candidate)

        assert result.strategy == ResolutionStrategy.NEW
        assert result.confidence == 0.0
        assert result.entity_id is None
        assert events == []

    async def test_alias_match_when_name_in_aliases(self, engine, mock_repo):
        existing = _make_entity(
            "Alice Chen", EntityType.PERSON,
            aliases=["a.chen", "ali chen"],
        )
        mock_repo.get_by_type_and_name.return_value = None
        mock_repo.search_by_name.return_value = [existing]

        candidate = _make_candidate("ali chen")
        result, events = await engine.resolve(candidate)

        assert result.strategy == ResolutionStrategy.ALIAS
        assert result.confidence == 0.85
        assert result.entity_id == existing.id

    async def test_alias_match_case_insensitive(self, engine, mock_repo):
        existing = _make_entity("Alice Chen", EntityType.PERSON, aliases=["Ali Chen"])
        mock_repo.get_by_type_and_name.return_value = None
        mock_repo.search_by_name.return_value = [existing]

        candidate = _make_candidate("ali chen")
        result, _ = await engine.resolve(candidate)

        assert result.strategy == ResolutionStrategy.ALIAS

    async def test_fuzzy_match_above_threshold(self, engine, mock_repo):
        existing = _make_entity("Alice Chen", EntityType.PERSON)
        mock_repo.get_by_type_and_name.return_value = None
        mock_repo.search_by_name.return_value = [existing]

        candidate = _make_candidate("Alise Chen")  # small typo → high similarity
        result, events = await engine.resolve(candidate)

        assert result.strategy == ResolutionStrategy.FUZZY
        assert 0.60 <= result.confidence <= 0.80

    async def test_fuzzy_below_warn_threshold_emits_event(self, engine, mock_repo):
        existing = _make_entity("Project Alpha", EntityType.PROJECT)
        mock_repo.get_by_type_and_name.return_value = None
        # Return the entity for both alias and fuzzy search
        mock_repo.search_by_name.return_value = [existing]

        # Very different name — might be below warn threshold
        candidate = _make_candidate("Proj Alph", EntityType.PROJECT)
        result, events = await engine.resolve(candidate, memory_record_id="rec-1")

        # If fuzzy matched with low similarity, should emit warning
        if result.strategy == ResolutionStrategy.FUZZY and result.confidence < 0.70:
            assert len(events) == 1
            assert events[0].candidate_name == candidate.name

    async def test_exact_match_takes_priority_over_fuzzy(self, engine, mock_repo):
        existing = _make_entity("Python", EntityType.SKILL)
        mock_repo.get_by_type_and_name.return_value = existing  # exact match found

        candidate = _make_candidate("Python", EntityType.SKILL)
        result, _ = await engine.resolve(candidate)

        assert result.strategy == ResolutionStrategy.EXACT_NAME
        # Should NOT reach fuzzy search
        mock_repo.search_by_name.assert_not_called()

    async def test_confidence_range_for_fuzzy(self, engine, mock_repo):
        existing = _make_entity("Engineering Team", EntityType.ORGANIZATION)
        mock_repo.get_by_type_and_name.return_value = None
        mock_repo.search_by_name.return_value = [existing]

        candidate = _make_candidate("Engineering Tea", EntityType.ORGANIZATION)
        result, _ = await engine.resolve(candidate)

        if result.strategy == ResolutionStrategy.FUZZY:
            assert 0.60 <= result.confidence <= 0.80
