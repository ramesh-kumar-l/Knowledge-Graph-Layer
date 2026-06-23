"""Unit tests for VersionService — mocks VersionRepository to test business logic."""
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.domain import SubjectType
from src.domain.version import Version
from src.services.version_service import VersionService


def _make_version(version_num: int, snapshot: dict) -> Version:
    return Version(
        subject_type=SubjectType.ENTITY,
        subject_id=uuid.uuid4(),
        version=version_num,
        snapshot=snapshot,
        changed_by="test",
    )


@pytest.fixture
def mock_version_repo():
    repo = AsyncMock()
    repo.get_latest = AsyncMock(return_value=None)
    repo.create = AsyncMock()
    repo.list_for_subject = AsyncMock(return_value=[])
    repo.get_by_version = AsyncMock(return_value=None)
    return repo


@pytest.fixture
def version_svc(mock_version_repo):
    return VersionService(mock_version_repo)


class TestVersionService:
    async def test_create_version_1_has_no_diff(self, version_svc, mock_version_repo):
        subject_id = uuid.uuid4()
        snapshot = {"name": "Alice", "type": "PERSON"}
        mock_version_repo.get_latest.return_value = None

        expected_version = _make_version(1, snapshot)
        mock_version_repo.create.return_value = expected_version

        await version_svc.create_version_before_write(
            subject_type=SubjectType.ENTITY,
            subject_id=subject_id,
            current_snapshot=snapshot,
            next_version=1,
            changed_by="system",
            change_reason="created",
        )

        call_args = mock_version_repo.create.call_args[0][0]
        assert call_args.diff is None  # no previous version → no diff
        assert call_args.version == 1

    async def test_diff_computed_from_previous_snapshot(self, version_svc, mock_version_repo):
        subject_id = uuid.uuid4()
        old_snapshot = {"name": "Alice", "type": "PERSON"}
        new_snapshot = {"name": "Alice Updated", "type": "PERSON"}

        prev_version = Version(
            subject_type=SubjectType.ENTITY,
            subject_id=subject_id,
            version=1,
            snapshot=old_snapshot,
            changed_by="system",
        )
        mock_version_repo.get_latest.return_value = prev_version
        mock_version_repo.create.return_value = _make_version(2, new_snapshot)

        await version_svc.create_version_before_write(
            subject_type=SubjectType.ENTITY,
            subject_id=subject_id,
            current_snapshot=new_snapshot,
            next_version=2,
            changed_by="user-1",
            change_reason="rename",
        )

        call_args = mock_version_repo.create.call_args[0][0]
        assert call_args.diff is not None
        # JSON Patch should reflect the name change
        assert any(op.get("op") == "replace" for op in call_args.diff)

    async def test_identical_snapshots_produce_empty_diff(self, version_svc, mock_version_repo):
        subject_id = uuid.uuid4()
        snapshot = {"name": "Alice", "type": "PERSON"}
        prev_version = Version(
            subject_type=SubjectType.ENTITY,
            subject_id=subject_id,
            version=1,
            snapshot=snapshot,
            changed_by="system",
        )
        mock_version_repo.get_latest.return_value = prev_version
        mock_version_repo.create.return_value = _make_version(2, snapshot)

        await version_svc.create_version_before_write(
            subject_type=SubjectType.ENTITY,
            subject_id=subject_id,
            current_snapshot=snapshot,
            next_version=2,
            changed_by="system",
        )

        call_args = mock_version_repo.create.call_args[0][0]
        assert call_args.diff == []  # empty patch — no changes

    async def test_get_history_delegates_to_repo(self, version_svc, mock_version_repo):
        subject_id = uuid.uuid4()
        await version_svc.get_history(SubjectType.ENTITY, subject_id)
        mock_version_repo.list_for_subject.assert_called_once_with(
            SubjectType.ENTITY, subject_id, offset=0, limit=50
        )
