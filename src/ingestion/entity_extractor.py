import re
import logging
from typing import Any

from src.domain.enums import EntityType
from src.ingestion.models import CandidateEntity, MemoryRecord
from src.ingestion.normalizer import normalize_name, normalize_attribute_keys

log = logging.getLogger(__name__)

_TYPE_KEYWORDS: dict[EntityType, list[str]] = {
    EntityType.PERSON: [
        "user", "person", "engineer", "developer", "author", "assignee",
        "manager", "researcher", "contact", "member", "employee",
    ],
    EntityType.PROJECT: [
        "project", "initiative", "repo", "repository", "codebase",
        "program", "workspace", "workstream",
    ],
    EntityType.GOAL: [
        "goal", "objective", "target", "milestone", "outcome",
        "aim", "mission", "okr",
    ],
    EntityType.TASK: [
        "task", "todo", "action", "issue", "ticket", "bug",
        "fix", "feature", "story", "backlog", "subtask",
    ],
    EntityType.SKILL: [
        "skill", "technology", "framework", "language", "expertise",
        "proficiency", "capability", "competency",
    ],
    EntityType.DOCUMENT: [
        "document", "file", "note", "report", "doc", "readme",
        "spec", "wiki", "page", "manual", "guide",
    ],
    EntityType.ORGANIZATION: [
        "company", "team", "organization", "org", "department",
        "group", "division", "unit", "firm",
    ],
    EntityType.EVENT: [
        "event", "meeting", "release", "sprint", "demo",
        "standup", "conference", "incident", "session", "launch",
    ],
    EntityType.CONCEPT: [
        "concept", "idea", "pattern", "principle", "theory",
        "approach", "method", "paradigm", "practice",
    ],
    EntityType.ARTIFACT: [
        "artifact", "binary", "dataset", "model",
        "config", "build", "package", "image", "container",
    ],
    EntityType.LOCATION: [
        "location", "place", "office", "city", "country",
        "region", "server", "cluster", "datacenter", "zone",
    ],
    EntityType.PRODUCT: [
        "product", "service", "platform", "app", "application",
        "software", "sdk", "library", "tool", "suite", "api",
    ],
}

_ENTITY_TYPE_DEFAULTS: dict[EntityType, dict[str, Any]] = {
    EntityType.TASK: {"status": "TODO"},
    EntityType.GOAL: {"status": "OPEN"},
    EntityType.PROJECT: {"status": "ACTIVE"},
    EntityType.PERSON: {},
    EntityType.SKILL: {},
    EntityType.DOCUMENT: {},
    EntityType.ORGANIZATION: {},
    EntityType.EVENT: {},
    EntityType.CONCEPT: {},
    EntityType.ARTIFACT: {},
    EntityType.LOCATION: {},
    EntityType.PRODUCT: {},
}

_QUOTED_RE = re.compile(r'"([^"]{2,80})"')
_AT_MENTION_RE = re.compile(r'@([\w][\w.\-]{1,49})')
_CAPITALIZED_RE = re.compile(r'\b([A-Z][a-z]{1,}(?:\s+[A-Z][a-z]{1,}){0,4})\b')

_STOPWORDS = frozenset({
    "the", "this", "that", "then", "there", "their", "they",
    "with", "from", "have", "been", "will", "when", "what",
    "which", "were", "are", "has", "but", "and", "for",
    "not", "can", "also", "all", "any", "its", "our",
})

# Common verb/gerund words that appear as first word of a phrase but are not entity names.
# Prevents extraction of spans like "Processing Project Alpha" that start with a verb.
_PHRASE_START_FILTER = frozenset({
    "processing", "working", "implementing", "creating", "using",
    "adding", "running", "testing", "fixing", "discussing", "meeting",
    "mentioned", "reviewing", "developing", "building", "designing",
    "analyzing", "deploying", "migrating", "refactoring", "updating",
    "checking", "verifying", "monitoring", "tracking", "assigning",
})


class EntityExtractor:
    """Rule-based entity extractor — three passes: metadata > patterns > heuristics."""

    def extract(self, record: MemoryRecord) -> list[CandidateEntity]:
        candidates: list[CandidateEntity] = []
        seen: set[str] = set()

        for c in (*self._from_metadata(record.metadata), *self._from_content(record.content)):
            key = f"{c.name.lower()}|{c.entity_type}"
            if key not in seen:
                seen.add(key)
                candidates.append(c)

        return candidates

    def _from_metadata(self, metadata: dict[str, Any]) -> list[CandidateEntity]:
        results = []
        for item in metadata.get("entities", []):
            if not isinstance(item, dict):
                continue
            raw_name = item.get("name", "").strip()
            type_str = item.get("type", "").upper()
            if not raw_name:
                continue
            try:
                etype = EntityType(type_str)
            except ValueError:
                etype = EntityType.CONCEPT
            defaults = _ENTITY_TYPE_DEFAULTS[etype].copy()
            extra_attrs = normalize_attribute_keys(item.get("attributes", {}))
            results.append(CandidateEntity(
                name=normalize_name(raw_name),
                entity_type=etype,
                aliases=item.get("aliases", []),
                attributes={**defaults, **extra_attrs},
                confidence=0.95,
                extraction_reason="metadata.entities",
            ))
        return results

    def _from_content(self, content: str) -> list[CandidateEntity]:
        results: list[CandidateEntity] = []

        for m in _QUOTED_RE.finditer(content):
            span = m.group(1).strip()
            if len(span.split()) > 6:
                continue
            etype, conf = self._classify(span, content)
            if etype is not None:
                results.append(CandidateEntity(
                    name=normalize_name(span),
                    entity_type=etype,
                    attributes=_ENTITY_TYPE_DEFAULTS[etype].copy(),
                    confidence=max(0.65, conf),
                    extraction_reason="quoted_string",
                ))

        for m in _AT_MENTION_RE.finditer(content):
            handle = m.group(1)
            display = normalize_name(re.sub(r"[.\-]", " ", handle))
            results.append(CandidateEntity(
                name=display,
                entity_type=EntityType.PERSON,
                aliases=[f"@{handle}"],
                attributes={},
                confidence=0.85,
                extraction_reason="at_mention",
            ))

        for m in _CAPITALIZED_RE.finditer(content):
            phrase = m.group(1).strip()
            first_word = phrase.split()[0].lower()
            if first_word in _PHRASE_START_FILTER:
                continue
            if phrase.lower() in _STOPWORDS or len(phrase) < 3:
                continue
            etype, conf = self._classify(phrase, content)
            if etype is not None and conf >= 0.60:
                results.append(CandidateEntity(
                    name=normalize_name(phrase),
                    entity_type=etype,
                    attributes=_ENTITY_TYPE_DEFAULTS[etype].copy(),
                    confidence=conf,
                    extraction_reason="capitalized_phrase",
                ))

        return results

    def _classify(self, name: str, context: str) -> tuple[EntityType | None, float]:
        """Score entity type by keyword presence in name (strong) and context (weak)."""
        lower_ctx = context.lower()
        lower_name = name.lower()
        best_type: EntityType | None = None
        best_score = 0.0

        for etype, keywords in _TYPE_KEYWORDS.items():
            score = sum(
                0.8 if kw in lower_name else (0.2 if kw in lower_ctx else 0.0)
                for kw in keywords
            )
            if score > best_score:
                best_score = score
                best_type = etype

        if best_type is None or best_score < 0.20:
            return None, 0.0

        confidence = min(0.85, 0.55 + min(best_score, 1.5) * 0.20)
        return best_type, confidence
