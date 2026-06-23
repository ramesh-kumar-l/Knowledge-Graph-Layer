from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator

from .enums import EntityType, VerificationState


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Entity(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    type: EntityType
    name: str = Field(min_length=1, max_length=512)
    aliases: list[str] = Field(default_factory=list)
    attributes: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    verification_state: VerificationState = VerificationState.UNVERIFIED
    source_memory_ids: list[str] = Field(default_factory=list)
    labels: list[str] = Field(default_factory=list)
    version: int = Field(default=1, ge=1)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
    is_active: bool = True

    model_config = {"frozen": False}

    def to_snapshot(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class CreateEntityCommand(BaseModel):
    type: EntityType
    name: str = Field(min_length=1, max_length=512)
    aliases: list[str] = Field(default_factory=list)
    attributes: dict[str, Any] = Field(default_factory=dict)
    source_memory_ids: list[str] = Field(default_factory=list)
    labels: list[str] = Field(default_factory=list)
    created_by: str = "system"


class UpdateEntityCommand(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=512)
    aliases: list[str] | None = None
    attributes: dict[str, Any] | None = None
    labels: list[str] | None = None
    verification_state: VerificationState | None = None
    change_reason: str = "update"
    changed_by: str = "system"

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str | None) -> str | None:
        if v is not None and not v.strip():
            raise ValueError("name cannot be blank")
        return v
