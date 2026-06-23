"""Initial schema — all 6 record types for SCP Knowledge Graph Layer.

Revision ID: 001
Revises:
Create Date: 2026-06-23
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "entities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("type", sa.String(64), nullable=False),
        sa.Column("name", sa.String(512), nullable=False),
        sa.Column("aliases", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("attributes", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("confidence", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("verification_state", sa.String(32), nullable=False, server_default="UNVERIFIED"),
        sa.Column("source_memory_ids", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("labels", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
    )
    op.create_index("ix_entities_type_name", "entities", ["type", "name"])
    op.create_index("ix_entities_verification_confidence", "entities", ["verification_state", "confidence"])
    op.create_index("ix_entities_is_active", "entities", ["is_active"])

    op.create_table(
        "relationships",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("type", sa.String(64), nullable=False),
        sa.Column("from_entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("to_entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("direction", sa.String(32), nullable=False, server_default="DIRECTED"),
        sa.Column("attributes", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("confidence", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("verification_state", sa.String(32), nullable=False, server_default="UNVERIFIED"),
        sa.Column("evidence_ids", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("provenance_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("strength", sa.Float, nullable=True),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
    )
    op.create_index("ix_relationships_from_type", "relationships", ["from_entity_id", "type"])
    op.create_index("ix_relationships_to_type", "relationships", ["to_entity_id", "type"])
    op.create_index("ix_relationships_type_confidence", "relationships", ["type", "confidence"])
    op.create_index("ix_relationships_is_active", "relationships", ["is_active"])

    op.create_table(
        "evidence",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("subject_type", sa.String(32), nullable=False),
        sa.Column("subject_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_type", sa.String(32), nullable=False),
        sa.Column("source_id", sa.String(512), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("confidence", sa.Float, nullable=False),
        sa.Column("extracted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("extractor_id", sa.String(256), nullable=False),
        sa.Column("verification_state", sa.String(32), nullable=False, server_default="UNVERIFIED"),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.UniqueConstraint("subject_id", "source_id", name="uq_evidence_subject_source"),
    )
    op.create_index("ix_evidence_subject", "evidence", ["subject_type", "subject_id"])
    op.create_index("ix_evidence_source_type", "evidence", ["source_type"])

    op.create_table(
        "provenance",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("subject_type", sa.String(32), nullable=False),
        sa.Column("subject_id", postgresql.UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column("origin", sa.String(256), nullable=False),
        sa.Column("extraction_method", sa.String(128), nullable=False),
        sa.Column("transformations", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("raw_source_ref", sa.String(512), nullable=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("agent_id", sa.String(256), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "trust_scores",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("subject_id", postgresql.UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column("score", sa.Float, nullable=False),
        sa.Column("evidence_weight", sa.Float, nullable=False),
        sa.Column("freshness_decay", sa.Float, nullable=False),
        sa.Column("verification_bonus", sa.Float, nullable=False),
        sa.Column("conflict_penalty", sa.Float, nullable=False),
        sa.Column("evidence_count", sa.Integer, nullable=False),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("algorithm", sa.String(32), nullable=False, server_default="v1"),
    )
    op.create_index("ix_trust_scores_score", "trust_scores", ["score"])
    op.create_index("ix_trust_scores_computed_at", "trust_scores", ["computed_at"])

    op.create_table(
        "versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("subject_type", sa.String(32), nullable=False),
        sa.Column("subject_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("snapshot", postgresql.JSONB, nullable=False),
        sa.Column("diff", postgresql.JSONB, nullable=True),
        sa.Column("changed_by", sa.String(256), nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("change_reason", sa.String(512), nullable=False, server_default=""),
        sa.UniqueConstraint("subject_id", "version", name="uq_versions_subject_version"),
    )
    op.create_index("ix_versions_subject_id", "versions", ["subject_id"])
    op.create_index("ix_versions_changed_at", "versions", ["changed_at"])


def downgrade() -> None:
    op.drop_table("versions")
    op.drop_table("trust_scores")
    op.drop_table("provenance")
    op.drop_table("evidence")
    op.drop_table("relationships")
    op.drop_table("entities")
