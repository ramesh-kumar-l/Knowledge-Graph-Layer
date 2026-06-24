"""Pydantic models for the SCP Knowledge Graph Layer API responses.

These mirror the backend domain models and are stable across API versions.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class EntityType(str, Enum):
    PERSON = "PERSON"
    ORGANIZATION = "ORGANIZATION"
    LOCATION = "LOCATION"
    EVENT = "EVENT"
    CONCEPT = "CONCEPT"
    PRODUCT = "PRODUCT"
    TECHNOLOGY = "TECHNOLOGY"
    DOCUMENT = "DOCUMENT"
    PROJECT = "PROJECT"
    TASK = "TASK"
    GOAL = "GOAL"
    OTHER = "OTHER"


class RelationshipType(str, Enum):
    RELATED_TO = "RELATED_TO"
    IS_PART_OF = "IS_PART_OF"
    HAS_PART = "HAS_PART"
    CAUSED_BY = "CAUSED_BY"
    CAUSES = "CAUSES"
    WORKS_FOR = "WORKS_FOR"
    EMPLOYS = "EMPLOYS"
    LOCATED_IN = "LOCATED_IN"
    CONTAINS = "CONTAINS"
    PARTICIPATES_IN = "PARTICIPATES_IN"
    HAS_PARTICIPANT = "HAS_PARTICIPANT"
    CREATED_BY = "CREATED_BY"
    CREATED = "CREATED"
    DEPENDS_ON = "DEPENDS_ON"
    REQUIRED_BY = "REQUIRED_BY"
    IS_SAME_AS = "IS_SAME_AS"
    IS_SIMILAR_TO = "IS_SIMILAR_TO"
    PRECEDES = "PRECEDES"
    FOLLOWS = "FOLLOWS"
    MENTIONS = "MENTIONS"
    MENTIONED_IN = "MENTIONED_IN"
    USES = "USES"
    USED_BY = "USED_BY"
    MANAGES = "MANAGES"
    MANAGED_BY = "MANAGED_BY"
    BELONGS_TO = "BELONGS_TO"
    HAS_MEMBER = "HAS_MEMBER"
    INFLUENCES = "INFLUENCES"
    INFLUENCED_BY = "INFLUENCED_BY"
    CONTRADICTS = "CONTRADICTS"
    SUPPORTS = "SUPPORTS"
    DERIVED_FROM = "DERIVED_FROM"
    SOURCE_OF = "SOURCE_OF"
    ASSOCIATED_WITH = "ASSOCIATED_WITH"
    CO_OCCURS_WITH = "CO_OCCURS_WITH"
    IMPLEMENTS = "IMPLEMENTS"
    IMPLEMENTED_BY = "IMPLEMENTED_BY"


class VerificationState(str, Enum):
    UNVERIFIED = "UNVERIFIED"
    VERIFIED = "VERIFIED"
    DISPUTED = "DISPUTED"
    RETRACTED = "RETRACTED"


class Direction(str, Enum):
    DIRECTED = "DIRECTED"
    BIDIRECTIONAL = "BIDIRECTIONAL"
    UNDIRECTED = "UNDIRECTED"


class ResolutionDecision(str, Enum):
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"


class Entity(BaseModel):
    id: UUID
    type: EntityType
    name: str
    aliases: list[str] = Field(default_factory=list)
    attributes: dict[str, Any] = Field(default_factory=dict)
    confidence: float
    verification_state: VerificationState
    source_record_ids: list[UUID] = Field(default_factory=list)
    is_active: bool
    created_at: datetime
    updated_at: datetime
    version: int


class Relationship(BaseModel):
    id: UUID
    type: RelationshipType
    from_entity_id: UUID
    to_entity_id: UUID
    direction: Direction
    confidence: float
    attributes: dict[str, Any] = Field(default_factory=dict)
    evidence_ids: list[UUID] = Field(default_factory=list)
    is_active: bool
    created_at: datetime
    updated_at: datetime


class TrustComponents(BaseModel):
    evidence_weight: float
    freshness_decay: float
    verification_bonus: float
    conflict_penalty: float


class TrustScore(BaseModel):
    entity_id: UUID
    overall_confidence: float
    components: TrustComponents
    computed_at: datetime


class GraphResponse(BaseModel):
    nodes: list[Entity]
    edges: list[Relationship]
    truncated: bool
    node_count: int
    edge_count: int


class PathResponse(BaseModel):
    entities: list[Entity]
    relationships: list[Relationship]
    hop_count: int
    total_confidence: float


class EvidenceItem(BaseModel):
    id: UUID
    entity_id: UUID
    content: str
    source: str
    confidence: float
    created_at: datetime


class ProvenanceInfo(BaseModel):
    entity_id: UUID
    source_system: str
    source_record_id: UUID | None
    ingested_by: str
    ingested_at: datetime


class ConflictEvent(BaseModel):
    entity_id: UUID
    detected_at: datetime
    resolved_at: datetime | None
    resolution: str | None
    resolved_by: str | None


class ExplainResponse(BaseModel):
    entity: Entity
    trust_score: TrustScore
    evidence: list[EvidenceItem]
    provenance: ProvenanceInfo | None
    conflict_history: list[ConflictEvent]


class MemoryRecord(BaseModel):
    id: UUID | None = None
    content: str
    source: str
    author: str | None = None
    tags: list[str] = Field(default_factory=list)
    attributes: dict[str, Any] = Field(default_factory=dict)


class CreateEntityCommand(BaseModel):
    type: EntityType
    name: str
    aliases: list[str] = Field(default_factory=list)
    attributes: dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0.5
    source_record_ids: list[UUID] = Field(default_factory=list)


class UpdateEntityCommand(BaseModel):
    name: str | None = None
    aliases: list[str] | None = None
    attributes: dict[str, Any] | None = None
    confidence: float | None = None


class CreateRelationshipCommand(BaseModel):
    type: RelationshipType
    from_entity_id: UUID
    to_entity_id: UUID
    direction: Direction = Direction.DIRECTED
    confidence: float = 0.5
    attributes: dict[str, Any] = Field(default_factory=dict)


class ResolveConflictCommand(BaseModel):
    decision: ResolutionDecision
    resolved_by: str = "user"
    reason: str = ""
