"""Fake archive adapter used for tests and local development without Feishu writes."""

from datetime import UTC, datetime

from ideaos_agent.domain.archive import (
    ArchiveDeleteResult,
    ArchiveProbeResult,
    ArchiveResult,
    ArchiveStatus,
    SessionArchivePayload,
    SessionArchiver,
)


class FakeSessionArchiver(SessionArchiver):
    """Return deterministic simulated results without external side effects."""

    def archive_session(self, payload: SessionArchivePayload) -> ArchiveResult:
        archived_at = datetime.now(UTC)
        return ArchiveResult(
            archive_status=ArchiveStatus.SIMULATED,
            archive_url=None,
            archive_error=None,
            archived_at=archived_at,
        )

    def delete_archive(self, archive_url: str) -> ArchiveDeleteResult:
        return ArchiveDeleteResult(
            archive_url=archive_url,
            deleted=True,
            archive_error=None,
        )

    def probe_archive(self, archive_url: str) -> ArchiveProbeResult:
        return ArchiveProbeResult(
            archive_url=archive_url,
            found=True,
            archive_error=None,
        )
