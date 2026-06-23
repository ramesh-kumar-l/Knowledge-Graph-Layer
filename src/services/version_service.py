"""Versioning enforcement service.

Write sequence (DEC-0006, ADR-0004 — must be inside one transaction):
  1. read current snapshot
  2. compute JSON Patch diff
  3. INSERT version record  ← create_version_before_write()
  4. caller applies the entity/relationship UPDATE
"""
import logging
from typing import Any
from uuid import UUID

import jsonpatch

from src.domain import Version, SubjectType
from src.domain.version import CreateVersionCommand
from src.repositories import VersionRepository

log = logging.getLogger(__name__)


class VersionService:
    def __init__(self, version_repo: VersionRepository) -> None:
        self._versions = version_repo

    async def create_version_before_write(
        self,
        subject_type: SubjectType,
        subject_id: UUID,
        current_snapshot: dict[str, Any],
        next_version: int,
        changed_by: str,
        change_reason: str = "",
    ) -> Version:
        """Compute diff from previous version and persist a new Version record.

        Must be called BEFORE the entity/relationship row is updated,
        inside the same transaction.
        """
        diff = await self._compute_diff(subject_type, subject_id, current_snapshot)

        cmd = CreateVersionCommand(
            subject_type=subject_type,
            subject_id=subject_id,
            version=next_version,
            snapshot=current_snapshot,
            diff=diff,
            changed_by=changed_by,
            change_reason=change_reason,
        )
        version = await self._versions.create(cmd)
        log.info(
            "version_created subject=%s version=%d changed_by=%s",
            subject_id, version.version, changed_by,
        )
        return version

    async def get_history(
        self,
        subject_type: SubjectType,
        subject_id: UUID,
        offset: int = 0,
        limit: int = 50,
    ) -> list[Version]:
        return await self._versions.list_for_subject(
            subject_type, subject_id, offset=offset, limit=limit
        )

    async def get_at_version(
        self,
        subject_id: UUID,
        version: int,
    ) -> Version | None:
        return await self._versions.get_by_version(subject_id, version)

    async def _compute_diff(
        self,
        subject_type: SubjectType,
        subject_id: UUID,
        current_snapshot: dict[str, Any],
    ) -> list[dict[str, Any]] | None:
        latest = await self._versions.get_latest(subject_type, subject_id)
        if latest is None:
            return None  # creation — no diff for version 1
        patch = jsonpatch.make_patch(latest.snapshot, current_snapshot)
        ops = list(patch)
        return ops if ops else []
