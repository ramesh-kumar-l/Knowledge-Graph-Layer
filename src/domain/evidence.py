from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from .enums import SubjectType, EvidenceSourceType, VerificationState

CONTENT_MAX_CHARS = 4096


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TransformationStep(BaseModel):
    step: str
    applied_at: datetime = Field(default_factory=_utcnow)
    applied_by: str


class Evidence(BaseModel):
    """Immutable after creation. Corrections add a new Evidence record."""

    id: UUID = Field(default_factory=uuid4)
    subject_type: SubjectType
    subject_id: UUID
    source_type: EvidenceSourceType
    source_id: str = Field(min_length=1)
    content: str = Field(max_length=CONTENT_MAX_CHARS)
    confidence: float = Field(ge=0.0, le=1.0)
    extracted_at: datetime = Field(default_factory=_utcnow)
    extractor_id: str
    verification_state: VerificationState = VerificationState.UNVERIFIED
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"frozen": True}  # immutable — corrections require new record


class CreateEvidenceCommand(BaseModel):
    subject_type: SubjectType
    subject_id: UUID
    source_type: EvidenceSourceType
    source_id: str = Field(min_length=1)
    content: str = Field(max_length=CONTENT_MAX_CHARS)
    confidence: float = Field(ge=0.0, le=1.0)
    extractor_id: str
    verification_state: VerificationState = VerificationState.UNVERIFIED
    metadata: dict[str, Any] = Field(default_factory=dict)
