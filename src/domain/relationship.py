from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, model_validator

from .enums import RelationshipType, Direction, VerificationState


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Relationship(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    type: RelationshipType
    from_entity_id: UUID
    to_entity_id: UUID
    direction: Direction = Direction.DIRECTED
    attributes: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    verification_state: VerificationState = VerificationState.UNVERIFIED
    evidence_ids: list[UUID] = Field(default_factory=list)
    provenance_id: UUID | None = None
    strength: float | None = Field(default=None, ge=0.0, le=1.0)
    version: int = Field(default=1, ge=1)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
    is_active: bool = True

    model_config = {"frozen": False}

    @model_validator(mode="after")
    def no_self_loop(self) -> "Relationship":
        if self.from_entity_id == self.to_entity_id:
            raise ValueError("from_entity_id and to_entity_id must differ (no self-loops)")
        return self

    def to_snapshot(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class CreateRelationshipCommand(BaseModel):
    type: RelationshipType
    from_entity_id: UUID
    to_entity_id: UUID
    direction: Direction = Direction.DIRECTED
    attributes: dict[str, Any] = Field(default_factory=dict)
    strength: float | None = Field(default=None, ge=0.0, le=1.0)
    created_by: str = "system"

    @model_validator(mode="after")
    def no_self_loop(self) -> "CreateRelationshipCommand":
        if self.from_entity_id == self.to_entity_id:
            raise ValueError("from_entity_id and to_entity_id must differ")
        return self
