from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from src.domain.enums import EntityType, RelationshipType


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class MemoryRecord(BaseModel):
    """Input record from SCP Memory Core (11-memory-model.md)."""

    id: str = Field(min_length=1)
    content: str
    timestamp: datetime
    session_id: UUID = Field(default_factory=uuid4)
    agent_id: str = "system"
    metadata: dict[str, Any] = Field(default_factory=dict)


class CandidateEntity(BaseModel):
    """Proposed entity extracted from a MemoryRecord, before identity resolution."""

    name: str
    entity_type: EntityType
    aliases: list[str] = Field(default_factory=list)
    attributes: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    extraction_reason: str = ""


class ResolutionStrategy(StrEnum):
    EXACT_ID = "EXACT_ID"
    EXACT_NAME = "EXACT_NAME"
    ALIAS = "ALIAS"
    FUZZY = "FUZZY"
    NEW = "NEW"


class ResolutionResult(BaseModel):
    strategy: ResolutionStrategy
    confidence: float
    entity_id: UUID | None = None  # None when strategy == NEW
    candidate: CandidateEntity


class IngestionResult(BaseModel):
    memory_record_id: str
    status: str  # "PROCESSED" | "SKIPPED_DUPLICATE"
    entities_created: int = 0
    entities_matched: int = 0
    relationships_created: int = 0
    relationships_skipped: int = 0
    events: list[dict[str, Any]] = Field(default_factory=list)


class ResolvedEntityRef(BaseModel):
    """Entity resolved by the entity pipeline — passed to relationship extraction."""

    entity_id: UUID
    entity_type: EntityType
    name: str
    aliases: list[str] = Field(default_factory=list)


class CandidateRelationship(BaseModel):
    """Proposed relationship extracted from MemoryRecord, before persistence."""

    from_entity_id: UUID
    from_entity_type: EntityType
    to_entity_id: UUID
    to_entity_type: EntityType
    relationship_type: RelationshipType
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    extraction_reason: str = ""


class RelationshipConstraintViolated(BaseModel):
    event_type: str = "RelationshipConstraintViolated"
    from_entity_id: UUID
    to_entity_id: UUID
    relationship_type: str
    from_entity_type: str
    to_entity_type: str
    timestamp: datetime = Field(default_factory=_utcnow)


class RelationshipCreatedEvent(BaseModel):
    event_type: str = "RelationshipCreatedEvent"
    relationship_id: UUID
    from_entity_id: UUID
    to_entity_id: UUID
    relationship_type: str
    memory_record_id: str
    timestamp: datetime = Field(default_factory=_utcnow)


class KnowledgeUpdatedEvent(BaseModel):
    event_type: str = "KnowledgeUpdatedEvent"
    entity_id: UUID
    memory_record_id: str
    timestamp: datetime = Field(default_factory=_utcnow)


class PotentialDuplicateDetected(BaseModel):
    event_type: str = "PotentialDuplicateDetected"
    candidate_name: str
    existing_entity_id: UUID | None = None
    confidence: float
    memory_record_id: str
    timestamp: datetime = Field(default_factory=_utcnow)


class KnowledgeConflictDetected(BaseModel):
    event_type: str = "KnowledgeConflictDetected"
    entity_id: UUID
    attribute: str
    evidence_ids: list[UUID]
    timestamp: datetime = Field(default_factory=_utcnow)
