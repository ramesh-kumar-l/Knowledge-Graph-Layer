"""Relationship Extractor — rule-based extraction of relationships between resolved entities.

Two extraction passes (highest confidence first):
  1. metadata.relationships — explicit declarations (0.90 confidence)
  2. verb-pattern matching in content sentences (0.65–0.85 confidence)
"""
import re
import logging
from dataclasses import dataclass

from src.domain.enums import RelationshipType
from src.ingestion.models import (
    MemoryRecord, CandidateRelationship, ResolvedEntityRef,
)

log = logging.getLogger(__name__)

_SENTENCE_RE = re.compile(r"[.!?\n]+")


@dataclass(frozen=True)
class _PatternRule:
    pattern: re.Pattern
    rel_type: RelationshipType
    confidence: float


# Each rule: pattern found between two entity mentions → (from_entity, to_entity, rel_type)
# Convention: left-of-pattern = from_entity, right-of-pattern = to_entity.
# Passive "by" constructs keep this convention (e.g. "Doc authored by Person" → Doc→Person).
_PATTERN_RULES: list[_PatternRule] = [
    _PatternRule(re.compile(r"\bassigned to\b", re.I), RelationshipType.ASSIGNED_TO, 0.85),
    _PatternRule(re.compile(r"\breports to\b|\breporting to\b", re.I), RelationshipType.REPORTS_TO, 0.85),
    _PatternRule(re.compile(r"\bworks toward\b|\bworking toward\b", re.I), RelationshipType.WORKS_TOWARD, 0.80),
    _PatternRule(re.compile(r"\bworks on\b|\bworking on\b", re.I), RelationshipType.WORKS_TOWARD, 0.72),
    _PatternRule(re.compile(r"\bcontributes to\b|\bcontributing to\b", re.I), RelationshipType.CONTRIBUTES_TO, 0.82),
    _PatternRule(re.compile(r"\bmember of\b|\bis a member of\b|\bbelongs to\b", re.I), RelationshipType.MEMBER_OF, 0.82),
    _PatternRule(re.compile(r"\bintegrates with\b|\bintegrated with\b", re.I), RelationshipType.INTEGRATES_WITH, 0.83),
    _PatternRule(re.compile(r"\bauthored by\b|\bwritten by\b", re.I), RelationshipType.AUTHORED_BY, 0.85),
    _PatternRule(re.compile(r"\bcreated by\b|\bbuilt by\b", re.I), RelationshipType.CREATED_BY, 0.83),
    _PatternRule(re.compile(r"\bmaintained by\b", re.I), RelationshipType.MAINTAINED_BY, 0.83),
    _PatternRule(re.compile(r"\bowned by\b", re.I), RelationshipType.OWNS, 0.80),
    _PatternRule(re.compile(r"\bowns\b", re.I), RelationshipType.OWNS, 0.80),
    _PatternRule(re.compile(r"\bdepends on\b|\bdependent on\b", re.I), RelationshipType.DEPENDS_ON, 0.83),
    _PatternRule(re.compile(r"\brequires\b", re.I), RelationshipType.REQUIRES, 0.78),
    _PatternRule(re.compile(r"\buses\b", re.I), RelationshipType.USES, 0.75),
    _PatternRule(re.compile(r"\bblocks\b|\bis blocking\b", re.I), RelationshipType.BLOCKS, 0.80),
    _PatternRule(re.compile(r"\benables\b|\benabling\b", re.I), RelationshipType.ENABLES, 0.78),
    _PatternRule(re.compile(r"\bpart of\b|\bcomponent of\b", re.I), RelationshipType.PART_OF, 0.78),
    _PatternRule(re.compile(r"\bcontains\b|\bincludes\b", re.I), RelationshipType.CONTAINS, 0.75),
    _PatternRule(re.compile(r"\bchild of\b", re.I), RelationshipType.CHILD_OF, 0.83),
    _PatternRule(re.compile(r"\bparent of\b", re.I), RelationshipType.PARENT_OF, 0.83),
    _PatternRule(re.compile(r"\bpreceded by\b|\bcomes after\b", re.I), RelationshipType.PRECEDED_BY, 0.80),
    _PatternRule(re.compile(r"\bfollowed by\b|\bcomes before\b", re.I), RelationshipType.FOLLOWED_BY, 0.80),
    _PatternRule(re.compile(r"\bscheduled on\b|\bscheduled for\b", re.I), RelationshipType.SCHEDULED_ON, 0.80),
    _PatternRule(re.compile(r"\brelated to\b", re.I), RelationshipType.RELATED_TO, 0.68),
    _PatternRule(re.compile(r"\bsimilar to\b", re.I), RelationshipType.SIMILAR_TO, 0.75),
    _PatternRule(re.compile(r"\bcontradicts\b|\bconflicts with\b", re.I), RelationshipType.CONTRADICTS, 0.78),
    _PatternRule(re.compile(r"\breferences\b", re.I), RelationshipType.REFERENCES, 0.72),
    _PatternRule(re.compile(r"\bderived from\b|\bbased on\b", re.I), RelationshipType.DERIVED_FROM, 0.78),
    _PatternRule(re.compile(r"\bcollaborates on\b|\bcollaborating on\b", re.I), RelationshipType.COLLABORATES_ON, 0.82),
    _PatternRule(re.compile(r"\bis alias of\b", re.I), RelationshipType.IS_ALIAS_OF, 0.83),
    _PatternRule(re.compile(r"\bis variation of\b", re.I), RelationshipType.IS_VARIATION_OF, 0.83),
    _PatternRule(re.compile(r"\bis same as\b", re.I), RelationshipType.IS_SAME_AS, 0.83),
]


class RelationshipExtractor:
    """Extracts candidate relationships from a MemoryRecord given already-resolved entities."""

    def extract(
        self,
        record: MemoryRecord,
        entities: list[ResolvedEntityRef],
    ) -> list[CandidateRelationship]:
        """Return deduplicated candidate relationships (highest confidence first)."""
        if len(entities) < 2:
            return []

        results: list[CandidateRelationship] = []
        seen: set[tuple] = set()

        for candidate in self._from_metadata(record.metadata, entities):
            key = (candidate.from_entity_id, candidate.to_entity_id, candidate.relationship_type)
            if key not in seen:
                seen.add(key)
                results.append(candidate)

        sorted_refs = sorted(entities, key=lambda r: len(r.name), reverse=True)
        for candidate in self._from_content(record.content, sorted_refs):
            key = (candidate.from_entity_id, candidate.to_entity_id, candidate.relationship_type)
            if key not in seen:
                seen.add(key)
                results.append(candidate)

        log.debug("relationship_extractor record=%s extracted=%d", record.id, len(results))
        return results

    def _from_metadata(
        self,
        metadata: dict,
        entities: list[ResolvedEntityRef],
    ) -> list[CandidateRelationship]:
        raw = metadata.get("relationships", [])
        if not isinstance(raw, list):
            return []

        name_map: dict[str, ResolvedEntityRef] = {}
        for ref in entities:
            name_map[ref.name.lower()] = ref
            for alias in ref.aliases:
                name_map[alias.lower()] = ref

        results = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            from_name = str(item.get("from", "")).strip()
            to_name = str(item.get("to", "")).strip()
            rel_type_str = str(item.get("type", "")).strip()
            confidence = float(item.get("confidence", 0.90))

            if not (from_name and to_name and rel_type_str):
                continue
            try:
                rel_type = RelationshipType(rel_type_str)
            except ValueError:
                continue

            from_ref = name_map.get(from_name.lower())
            to_ref = name_map.get(to_name.lower())
            if not (from_ref and to_ref) or from_ref.entity_id == to_ref.entity_id:
                continue

            results.append(CandidateRelationship(
                from_entity_id=from_ref.entity_id,
                from_entity_type=from_ref.entity_type,
                to_entity_id=to_ref.entity_id,
                to_entity_type=to_ref.entity_type,
                relationship_type=rel_type,
                confidence=min(confidence, 0.95),
                extraction_reason="metadata",
            ))
        return results

    def _from_content(
        self,
        content: str,
        sorted_refs: list[ResolvedEntityRef],
    ) -> list[CandidateRelationship]:
        results = []
        for sentence in _SENTENCE_RE.split(content):
            sentence = sentence.strip()
            if not sentence:
                continue
            results.extend(self._extract_from_sentence(sentence, sorted_refs))
        return results

    def _extract_from_sentence(
        self,
        sentence: str,
        sorted_refs: list[ResolvedEntityRef],
    ) -> list[CandidateRelationship]:
        results = []
        sent_lower = sentence.lower()

        for rule in _PATTERN_RULES:
            match = rule.pattern.search(sent_lower)
            if not match:
                continue

            left_text = sentence[: match.start()]
            right_text = sentence[match.end():]

            from_ref = self._find_entity(left_text, sorted_refs)
            to_ref = self._find_entity(right_text, sorted_refs)

            if from_ref and to_ref and from_ref.entity_id != to_ref.entity_id:
                results.append(CandidateRelationship(
                    from_entity_id=from_ref.entity_id,
                    from_entity_type=from_ref.entity_type,
                    to_entity_id=to_ref.entity_id,
                    to_entity_type=to_ref.entity_type,
                    relationship_type=rule.rel_type,
                    confidence=rule.confidence,
                    extraction_reason=f"pattern:{rule.pattern.pattern[:40]}",
                ))

        return results

    @staticmethod
    def _find_entity(
        text: str,
        sorted_refs: list[ResolvedEntityRef],
    ) -> ResolvedEntityRef | None:
        """Return the first (longest) entity name found in text."""
        text_lower = text.lower()
        for ref in sorted_refs:
            if ref.name.lower() in text_lower:
                return ref
            for alias in ref.aliases:
                if alias.lower() in text_lower:
                    return ref
        return None
