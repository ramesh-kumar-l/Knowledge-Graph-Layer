import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, DateTime, Float, Index, Integer,
    String, Text, UniqueConstraint, Uuid,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import JSON


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class EntityORM(Base):
    __tablename__ = "entities"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    type: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    aliases: Mapped[dict] = mapped_column(JSON, nullable=False, default=list)
    attributes: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    verification_state: Mapped[str] = mapped_column(String(32), nullable=False, default="UNVERIFIED")
    source_memory_ids: Mapped[dict] = mapped_column(JSON, nullable=False, default=list)
    labels: Mapped[dict] = mapped_column(JSON, nullable=False, default=list)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    __table_args__ = (
        Index("ix_entities_type_name", "type", "name"),
        Index("ix_entities_verification_confidence", "verification_state", "confidence"),
        Index("ix_entities_is_active", "is_active"),
    )


class RelationshipORM(Base):
    __tablename__ = "relationships"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    type: Mapped[str] = mapped_column(String(64), nullable=False)
    from_entity_id: Mapped[uuid.UUID] = mapped_column(Uuid(), nullable=False)
    to_entity_id: Mapped[uuid.UUID] = mapped_column(Uuid(), nullable=False)
    direction: Mapped[str] = mapped_column(String(32), nullable=False, default="DIRECTED")
    attributes: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    verification_state: Mapped[str] = mapped_column(String(32), nullable=False, default="UNVERIFIED")
    evidence_ids: Mapped[dict] = mapped_column(JSON, nullable=False, default=list)
    provenance_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(), nullable=True)
    strength: Mapped[float | None] = mapped_column(Float, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    __table_args__ = (
        Index("ix_relationships_from_type", "from_entity_id", "type"),
        Index("ix_relationships_to_type", "to_entity_id", "type"),
        Index("ix_relationships_type_confidence", "type", "confidence"),
        Index("ix_relationships_is_active", "is_active"),
    )


class EvidenceORM(Base):
    __tablename__ = "evidence"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    subject_type: Mapped[str] = mapped_column(String(32), nullable=False)
    subject_id: Mapped[uuid.UUID] = mapped_column(Uuid(), nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_id: Mapped[str] = mapped_column(String(512), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    extracted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow)
    extractor_id: Mapped[str] = mapped_column(String(256), nullable=False)
    verification_state: Mapped[str] = mapped_column(String(32), nullable=False, default="UNVERIFIED")
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)

    __table_args__ = (
        UniqueConstraint("subject_id", "source_id", name="uq_evidence_subject_source"),
        Index("ix_evidence_subject", "subject_type", "subject_id"),
        Index("ix_evidence_source_type", "source_type"),
    )


class ProvenanceORM(Base):
    __tablename__ = "provenance"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    subject_type: Mapped[str] = mapped_column(String(32), nullable=False)
    subject_id: Mapped[uuid.UUID] = mapped_column(Uuid(), nullable=False, unique=True)
    origin: Mapped[str] = mapped_column(String(256), nullable=False)
    extraction_method: Mapped[str] = mapped_column(String(128), nullable=False)
    transformations: Mapped[dict] = mapped_column(JSON, nullable=False, default=list)
    raw_source_ref: Mapped[str | None] = mapped_column(String(512), nullable=True)
    session_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(), nullable=True)
    agent_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow)


class TrustScoreORM(Base):
    __tablename__ = "trust_scores"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    subject_id: Mapped[uuid.UUID] = mapped_column(Uuid(), nullable=False, unique=True)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    evidence_weight: Mapped[float] = mapped_column(Float, nullable=False)
    freshness_decay: Mapped[float] = mapped_column(Float, nullable=False)
    verification_bonus: Mapped[float] = mapped_column(Float, nullable=False)
    conflict_penalty: Mapped[float] = mapped_column(Float, nullable=False)
    evidence_count: Mapped[int] = mapped_column(Integer, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow)
    algorithm: Mapped[str] = mapped_column(String(32), nullable=False, default="v1")

    __table_args__ = (
        Index("ix_trust_scores_score", "score"),
        Index("ix_trust_scores_computed_at", "computed_at"),
    )


class VersionORM(Base):
    __tablename__ = "versions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    subject_type: Mapped[str] = mapped_column(String(32), nullable=False)
    subject_id: Mapped[uuid.UUID] = mapped_column(Uuid(), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    diff: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    changed_by: Mapped[str] = mapped_column(String(256), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow)
    change_reason: Mapped[str] = mapped_column(String(512), nullable=False, default="")

    __table_args__ = (
        UniqueConstraint("subject_id", "version", name="uq_versions_subject_version"),
        Index("ix_versions_subject_id", "subject_id"),
        Index("ix_versions_changed_at", "changed_at"),
    )
