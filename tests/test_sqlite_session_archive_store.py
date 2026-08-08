import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from ideaos_agent.domain.analysis import IdeaAnalysis
from ideaos_agent.domain.archive import ArchiveStatus, SessionRecord
from ideaos_agent.domain.session import SessionKind, SessionSnapshot
from ideaos_agent.infrastructure.archive.sqlite_store import SqliteSessionArchiveStore


def test_sqlite_store_creates_and_reads_session_record(tmp_path: Path) -> None:
    db_path = tmp_path / "ideaos_agent.db"
    store = SqliteSessionArchiveStore(db_path)
    record = SessionRecord(
        session_id="sess_first",
        root_session_id="sess_first",
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
    assert fetched_record.root_session_id == "sess_first"
    assert fetched_record.archive_status == ArchiveStatus.NOT_TRIGGERED
    assert fetched_record.completed_at is None


def test_sqlite_store_updates_existing_session_record(tmp_path: Path) -> None:
    db_path = tmp_path / "ideaos_agent.db"
    store = SqliteSessionArchiveStore(db_path)
    first_record = SessionRecord(
        session_id="sess_existing",
        root_session_id="sess_existing",
        original_content="我想做一个帮助独立开发者验证产品想法的工具。",
        input_echo="我想做一个帮助独立开发者验证产品想法的工具。",
        clarification_count=0,
        archive_status=ArchiveStatus.NOT_TRIGGERED,
    )
    created_record = store.save_session_record(first_record)

    updated_record = SessionRecord(
        session_id="sess_existing",
        root_session_id="sess_existing",
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
    assert fetched_record.root_session_id == "sess_existing"
    assert fetched_record.clarification_count == 2
    assert fetched_record.archive_status == ArchiveStatus.PENDING


def test_sqlite_store_reads_old_analysis_row_without_root_session_id_value(tmp_path: Path) -> None:
    db_path = tmp_path / "ideaos_agent.db"
    store = SqliteSessionArchiveStore(db_path)

    with sqlite3.connect(db_path) as connection:
        connection.execute("UPDATE session_records SET root_session_id = ''")

    fetched_record = store.get_session_record("missing")
    assert fetched_record is None

    record = SessionRecord(
        session_id="sess_legacy_analysis",
        root_session_id="sess_legacy_analysis",
        original_content="我想做一个帮助独立开发者验证产品想法的工具。",
        input_echo="我想做一个帮助独立开发者验证产品想法的工具。",
        clarification_count=0,
        archive_status=ArchiveStatus.NOT_TRIGGERED,
    )
    store.save_session_record(record)

    with sqlite3.connect(db_path) as connection:
        connection.execute(
            "UPDATE session_records SET root_session_id = '' WHERE session_id = ?",
            ("sess_legacy_analysis",),
        )

    fetched_record = store.get_session_record("sess_legacy_analysis")

    assert fetched_record is not None
    assert fetched_record.root_session_id == "sess_legacy_analysis"


def test_sqlite_store_migrates_legacy_fake_archive_url(tmp_path: Path) -> None:
    db_path = tmp_path / "ideaos_agent.db"
    store = SqliteSessionArchiveStore(db_path)
    archived_at = datetime.now(UTC)
    legacy_record = SessionRecord(
        session_id="sess_legacy_fake",
        root_session_id="sess_legacy_fake",
        original_content="我想验证模拟归档不会生成外链。",
        input_echo="我想验证模拟归档不会生成外链。",
        clarification_count=0,
        archive_status=ArchiveStatus.SUCCEEDED,
        archive_url="https://feishu.example.com/docx/sess_legacy_fake",
        completed_at=archived_at,
        archived_at=archived_at,
    )
    store.save_session_record(legacy_record)

    migrated_store = SqliteSessionArchiveStore(db_path)
    migrated_record = migrated_store.get_session_record("sess_legacy_fake")

    assert migrated_record is not None
    assert migrated_record.archive_status == ArchiveStatus.SIMULATED
    assert migrated_record.archive_url is None
    assert migrated_record.archived_at == archived_at


def test_sqlite_store_round_trips_snapshot_with_intent(tmp_path: Path) -> None:
    db_path = tmp_path / "ideaos_agent.db"
    store = SqliteSessionArchiveStore(db_path)
    snapshot = SessionSnapshot(
        session_id="sess_intent",
        root_session_id="sess_intent",
        session_kind=SessionKind.ANALYSIS,
        archive_title="个人效率小工具",
        original_content="我想做一个给自己用的记账小工具。",
        input_echo="我想做一个给自己用的记账小工具。",
        intent="personal",
        analysis=IdeaAnalysis(
            summary="一个给自己用的记账小工具。",
            feasibility="简单可行。",
            market="个人自用价值与成本。",
        ),
        completed_at=datetime.now(UTC),
    )

    saved = store.save_session_snapshot(snapshot)
    fetched = store.get_session_snapshot("sess_intent")

    assert saved.intent == "personal"
    assert fetched is not None
    assert fetched.intent == "personal"
    assert fetched.analysis is not None
    assert fetched.analysis.market == "个人自用价值与成本。"

