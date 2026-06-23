import logging
from difflib import SequenceMatcher

from src.repositories import EntityRepository
from src.ingestion.models import (
    CandidateEntity, ResolutionResult, ResolutionStrategy,
    PotentialDuplicateDetected,
)
from src.ingestion.normalizer import normalize_for_comparison

log = logging.getLogger(__name__)

_FUZZY_MIN_SIMILARITY = 0.60
_FUZZY_WARN_THRESHOLD = 0.70  # below this, emit PotentialDuplicateDetected


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def _fuzzy_confidence(sim: float) -> float:
    """Map similarity [0.60, 1.0] → confidence [0.60, 0.80]."""
    return round(0.60 + (sim - 0.60) * 0.50, 3)


class DeduplicationEngine:
    """Identity resolution engine (11-memory-model.md confidence table).

    Strategy priority:
      EXACT_NAME  → 0.90  (exact name + type DB match)
      ALIAS       → 0.85  (candidate name matches stored alias)
      FUZZY       → 0.60–0.80  (Levenshtein similarity ≥ 0.60)
      NEW         → 0.00  (no match — create new entity)
    """

    def __init__(self, entity_repo: EntityRepository) -> None:
        self._repo = entity_repo

    async def resolve(
        self,
        candidate: CandidateEntity,
        memory_record_id: str = "",
    ) -> tuple[ResolutionResult, list[PotentialDuplicateDetected]]:
        """Resolve a single candidate. Returns (result, warning_events)."""
        events: list[PotentialDuplicateDetected] = []

        result = await self._exact_name_match(candidate)
        if result:
            return result, events

        result = await self._alias_match(candidate)
        if result:
            return result, events

        result, event = await self._fuzzy_match(candidate, memory_record_id)
        if result:
            if event:
                events.append(event)
            return result, events

        return ResolutionResult(
            strategy=ResolutionStrategy.NEW,
            confidence=0.0,
            entity_id=None,
            candidate=candidate,
        ), events

    async def _exact_name_match(self, candidate: CandidateEntity) -> ResolutionResult | None:
        entity = await self._repo.get_by_type_and_name(candidate.entity_type, candidate.name)
        if entity:
            log.debug("dedup exact_name: %s → %s", candidate.name, entity.id)
            return ResolutionResult(
                strategy=ResolutionStrategy.EXACT_NAME,
                confidence=0.9,
                entity_id=entity.id,
                candidate=candidate,
            )
        return None

    async def _alias_match(self, candidate: CandidateEntity) -> ResolutionResult | None:
        norm = normalize_for_comparison(candidate.name)
        nearby = await self._repo.search_by_name(
            candidate.name, entity_type=candidate.entity_type,
            min_confidence=0.0, limit=20,
        )
        for entity in nearby:
            for alias in entity.aliases:
                if normalize_for_comparison(alias) == norm:
                    log.debug("dedup alias: %s → %s", candidate.name, entity.id)
                    return ResolutionResult(
                        strategy=ResolutionStrategy.ALIAS,
                        confidence=0.85,
                        entity_id=entity.id,
                        candidate=candidate,
                    )
        return None

    async def _fuzzy_match(
        self,
        candidate: CandidateEntity,
        memory_record_id: str,
    ) -> tuple[ResolutionResult | None, PotentialDuplicateDetected | None]:
        norm_candidate = normalize_for_comparison(candidate.name)
        prefix = candidate.name[:3] if len(candidate.name) >= 3 else candidate.name
        nearby = await self._repo.search_by_name(
            prefix, entity_type=candidate.entity_type,
            min_confidence=0.0, limit=30,
        )
        best_entity = None
        best_sim = 0.0
        for entity in nearby:
            sim = _similarity(norm_candidate, normalize_for_comparison(entity.name))
            if sim > best_sim:
                best_sim = sim
                best_entity = entity

        if best_sim < _FUZZY_MIN_SIMILARITY or best_entity is None:
            return None, None

        confidence = _fuzzy_confidence(best_sim)
        log.debug("dedup fuzzy: %s → %s (sim=%.2f)", candidate.name, best_entity.id, best_sim)

        event = None
        if best_sim < _FUZZY_WARN_THRESHOLD:
            event = PotentialDuplicateDetected(
                candidate_name=candidate.name,
                existing_entity_id=best_entity.id,
                confidence=confidence,
                memory_record_id=memory_record_id,
            )
        return ResolutionResult(
            strategy=ResolutionStrategy.FUZZY,
            confidence=confidence,
            entity_id=best_entity.id,
            candidate=candidate,
        ), event
