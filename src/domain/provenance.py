from datetime import datetime, timezone
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from .enums import SubjectType
from .evidence import TransformationStep


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Provenance(BaseModel):
    """Chain of custody. Exactly one record per Entity or Relationship."""

    id: UUID = Field(default_factory=uuid4)
    subject_type: SubjectType
    subject_id: UUID
    origin: str
    extraction_method: str
    transformations: list[TransformationStep] = Field(default_factory=list)
    raw_source_ref: str | None = None
    session_id: UUID | None = None
    agent_id: str | None = None
    timestamp: datetime = Field(default_factory=_utcnow)

    model_config = {"frozen": True}


class CreateProvenanceCommand(BaseModel):
    subject_type: SubjectType
    subject_id: UUID
    origin: str
    extraction_method: str
    transformations: list[TransformationStep] = Field(default_factory=list)
    raw_source_ref: str | None = None
    session_id: UUID | None = None
    agent_id: str | None = None
