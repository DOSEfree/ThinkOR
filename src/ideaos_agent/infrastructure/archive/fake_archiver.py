"""Fake archive adapter used for tests and local development without Feishu writes."""

from datetime import UTC, datetime

from ideaos_agent.domain.archive import (
    ArchiveResult,
    ArchiveStatus,
    SessionArchivePayload,
    SessionArchiver,
)


class FakeSessionArchiver(SessionArchiver):
    """Return deterministic archive success results without external side effects."""

    def archive_session(self, payload: SessionArchivePayload) -> ArchiveResult:
        archived_at = datetime.now(UTC)
        return ArchiveResult(
            archive_status=ArchiveStatus.SUCCEEDED,
            archive_url=f"https://feishu.example.com/docx/{payload.session_id}",
            archive_error=None,
            archived_at=archived_at,
        )
