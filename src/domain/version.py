from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from .enums import SubjectType


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Version(BaseModel):
    """Immutable snapshot. Append-only — past versions are never mutated."""

    id: UUID = Field(default_factory=uuid4)
    subject_type: SubjectType
    subject_id: UUID
    version: int = Field(ge=1)
    snapshot: dict[str, Any]
    diff: list[dict[str, Any]] | None = None  # JSON Patch operations
    changed_by: str
    changed_at: datetime = Field(default_factory=_utcnow)
    change_reason: str = ""

    model_config = {"frozen": True}


class CreateVersionCommand(BaseModel):
    subject_type: SubjectType
    subject_id: UUID
    version: int = Field(ge=1)
    snapshot: dict[str, Any]
    diff: list[dict[str, Any]] | None = None
    changed_by: str
    change_reason: str = ""
