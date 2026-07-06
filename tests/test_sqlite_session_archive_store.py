from datetime import UTC, datetime
from pathlib import Path

from ideaos_agent.domain.archive import ArchiveStatus, SessionRecord
from ideaos_agent.infrastructure.archive.sqlite_store import SqliteSessionArchiveStore


def test_sqlite_store_creates_and_reads_session_record(tmp_path: Path) -> None:
    db_path = tmp_path / "ideaos_agent.db"
    store = SqliteSessionArchiveStore(db_path)
    record = SessionRecord(
        session_id="sess_first",
        original_content="我想做一个帮助独立开发者验证产品想法的工具。",
        input_echo="我想做一个帮助独立开发者验证产品想法的工具。",
        clarification_count=0,
        archive_status=ArchiveStatus.NOT_TRIGGERED,
    )

    saved_record = store.save_session_record(record)
    fetched_record = store.get_session_record("sess_first")

    assert db_path.exists()
    assert saved_record.session_id == "sess_first"
    assert fetched_record is not None
    assert fetched_record.archive_status == ArchiveStatus.NOT_TRIGGERED
    assert fetched_record.completed_at is None


def test_sqlite_store_updates_existing_session_record(tmp_path: Path) -> None:
    db_path = tmp_path / "ideaos_agent.db"
    store = SqliteSessionArchiveStore(db_path)
    first_record = SessionRecord(
        session_id="sess_existing",
        original_content="我想做一个帮助独立开发者验证产品想法的工具。",
        input_echo="我想做一个帮助独立开发者验证产品想法的工具。",
        clarification_count=0,
        archive_status=ArchiveStatus.NOT_TRIGGERED,
    )
    created_record = store.save_session_record(first_record)

    updated_record = SessionRecord(
        session_id="sess_existing",
        original_content="我想做一个帮助独立开发者验证产品想法的工具。",
        input_echo="我想做一个帮助独立开发者验证产品想法的工具。",
        clarification_count=2,
        archive_status=ArchiveStatus.PENDING,
        completed_at=datetime.now(UTC),
    )
    saved_record = store.save_session_record(updated_record)
    fetched_record = store.get_session_record("sess_existing")

    assert saved_record.clarification_count == 2
    assert saved_record.archive_status == ArchiveStatus.PENDING
    assert saved_record.completed_at is not None
    assert fetched_record is not None
    assert fetched_record.created_at == created_record.created_at
    assert fetched_record.clarification_count == 2
    assert fetched_record.archive_status == ArchiveStatus.PENDING
