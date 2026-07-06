"""SQLite-backed session index and snapshot storage."""

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from ideaos_agent.domain.analysis import IdeaAnalysis, RefinementResult
from ideaos_agent.domain.archive import ArchiveStatus, SessionArchiveStore, SessionRecord
from ideaos_agent.domain.session import (
    SessionClarificationRecord,
    SessionKind,
    SessionSnapshot,
    SessionSnapshotStore,
)


class SqliteSessionArchiveStore(SessionArchiveStore, SessionSnapshotStore):
    """Persist session index records and structured snapshots in SQLite."""

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = Path(db_path)
        self._initialize()

    def save_session_record(self, record: SessionRecord) -> SessionRecord:
        """Create or update a session index record while preserving first-created time."""

        existing = self.get_session_record(record.session_id)
        persisted_record = record
        if existing is not None:
            persisted_record = record.model_copy(update={"created_at": existing.created_at})

        with self._connect() as connection:
            if existing is None:
                connection.execute(
                    """
                    INSERT INTO session_records (
                        session_id,
                        parent_session_id,
                        session_kind,
                        original_content,
                        input_echo,
                        clarification_count,
                        archive_status,
                        archive_url,
                        archive_error,
                        created_at,
                        completed_at,
                        archived_at,
                        updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    self._record_to_row(persisted_record),
                )
            else:
                connection.execute(
                    """
                    UPDATE session_records
                    SET
                        parent_session_id = ?,
                        session_kind = ?,
                        original_content = ?,
                        input_echo = ?,
                        clarification_count = ?,
                        archive_status = ?,
                        archive_url = ?,
                        archive_error = ?,
                        completed_at = ?,
                        archived_at = ?,
                        updated_at = ?
                    WHERE session_id = ?
                    """,
                    (
                        persisted_record.parent_session_id,
                        persisted_record.session_kind.value,
                        persisted_record.original_content,
                        persisted_record.input_echo,
                        persisted_record.clarification_count,
                        persisted_record.archive_status.value,
                        persisted_record.archive_url,
                        persisted_record.archive_error,
                        self._serialize_datetime(persisted_record.completed_at),
                        self._serialize_datetime(persisted_record.archived_at),
                        self._serialize_datetime(persisted_record.updated_at),
                        persisted_record.session_id,
                    ),
                )

        saved_record = self.get_session_record(persisted_record.session_id)
        if saved_record is None:
            raise RuntimeError("SQLite session record could not be read back after save.")
        return saved_record

    def get_session_record(self, session_id: str) -> SessionRecord | None:
        """Fetch a session index record by ID."""

        normalized_session_id = self._normalize_session_id(session_id)
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    session_id,
                    parent_session_id,
                    session_kind,
                    original_content,
                    input_echo,
                    clarification_count,
                    archive_status,
                    archive_url,
                    archive_error,
                    created_at,
                    completed_at,
                    archived_at,
                    updated_at
                FROM session_records
                WHERE session_id = ?
                """,
                (normalized_session_id,),
            ).fetchone()

        if row is None:
            return None

        return SessionRecord(
            session_id=str(row["session_id"]),
            parent_session_id=self._nullable_text(row["parent_session_id"]),
            session_kind=SessionKind(str(row["session_kind"])),
            original_content=str(row["original_content"]),
            input_echo=str(row["input_echo"]),
            clarification_count=int(row["clarification_count"]),
            archive_status=ArchiveStatus(str(row["archive_status"])),
            archive_url=self._nullable_text(row["archive_url"]),
            archive_error=self._nullable_text(row["archive_error"]),
            created_at=self._parse_required_datetime(str(row["created_at"])),
            completed_at=self._parse_datetime(row["completed_at"]),
            archived_at=self._parse_datetime(row["archived_at"]),
            updated_at=self._parse_required_datetime(str(row["updated_at"])),
        )

    def save_session_snapshot(self, snapshot: SessionSnapshot) -> SessionSnapshot:
        """Create or update a structured session snapshot while preserving created_at."""

        existing = self.get_session_snapshot(snapshot.session_id)
        persisted_snapshot = snapshot
        if existing is not None:
            persisted_snapshot = snapshot.model_copy(update={"created_at": existing.created_at})

        with self._connect() as connection:
            if existing is None:
                connection.execute(
                    """
                    INSERT INTO session_snapshots (
                        session_id,
                        parent_session_id,
                        session_kind,
                        archive_title,
                        original_content,
                        input_echo,
                        follow_up_question,
                        clarifications_json,
                        assumptions_json,
                        open_questions_json,
                        analysis_json,
                        refinement_json,
                        created_at,
                        completed_at,
                        archived_at,
                        updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    self._snapshot_to_row(persisted_snapshot),
                )
            else:
                connection.execute(
                    """
                    UPDATE session_snapshots
                    SET
                        parent_session_id = ?,
                        session_kind = ?,
                        archive_title = ?,
                        original_content = ?,
                        input_echo = ?,
                        follow_up_question = ?,
                        clarifications_json = ?,
                        assumptions_json = ?,
                        open_questions_json = ?,
                        analysis_json = ?,
                        refinement_json = ?,
                        completed_at = ?,
                        archived_at = ?,
                        updated_at = ?
                    WHERE session_id = ?
                    """,
                    (
                        persisted_snapshot.parent_session_id,
                        persisted_snapshot.session_kind.value,
                        persisted_snapshot.archive_title,
                        persisted_snapshot.original_content,
                        persisted_snapshot.input_echo,
                        persisted_snapshot.follow_up_question,
                        self._to_json(
                            [item.model_dump() for item in persisted_snapshot.clarifications]
                        ),
                        self._to_json(persisted_snapshot.assumptions),
                        self._to_json(persisted_snapshot.open_questions),
                        self._to_json(
                            persisted_snapshot.analysis.model_dump()
                            if persisted_snapshot.analysis is not None
                            else None
                        ),
                        self._to_json(
                            persisted_snapshot.refinement_result.model_dump()
                            if persisted_snapshot.refinement_result is not None
                            else None
                        ),
                        self._serialize_datetime(persisted_snapshot.completed_at),
                        self._serialize_datetime(persisted_snapshot.archived_at),
                        self._serialize_datetime(persisted_snapshot.updated_at),
                        persisted_snapshot.session_id,
                    ),
                )

        saved_snapshot = self.get_session_snapshot(persisted_snapshot.session_id)
        if saved_snapshot is None:
            raise RuntimeError("SQLite session snapshot could not be read back after save.")
        return saved_snapshot

    def get_session_snapshot(self, session_id: str) -> SessionSnapshot | None:
        """Fetch a structured session snapshot by ID."""

        normalized_session_id = self._normalize_session_id(session_id)
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    session_id,
                    parent_session_id,
                    session_kind,
                    archive_title,
                    original_content,
                    input_echo,
                    follow_up_question,
                    clarifications_json,
                    assumptions_json,
                    open_questions_json,
                    analysis_json,
                    refinement_json,
                    created_at,
                    completed_at,
                    archived_at,
                    updated_at
                FROM session_snapshots
                WHERE session_id = ?
                """,
                (normalized_session_id,),
            ).fetchone()

        if row is None:
            return None

        clarifications_data = self._from_json(str(row["clarifications_json"]))
        assumptions_data = self._from_json(str(row["assumptions_json"]))
        open_questions_data = self._from_json(str(row["open_questions_json"]))
        analysis_data = self._nullable_json(row["analysis_json"])
        refinement_data = self._nullable_json(row["refinement_json"])

        return SessionSnapshot(
            session_id=str(row["session_id"]),
            parent_session_id=self._nullable_text(row["parent_session_id"]),
            session_kind=SessionKind(str(row["session_kind"])),
            archive_title=str(row["archive_title"]),
            original_content=str(row["original_content"]),
            input_echo=str(row["input_echo"]),
            follow_up_question=self._nullable_text(row["follow_up_question"]),
            clarifications=[
                SessionClarificationRecord.model_validate(item) for item in clarifications_data
            ],
            assumptions=[str(item) for item in assumptions_data],
            open_questions=[str(item) for item in open_questions_data],
            analysis=(
                IdeaAnalysis.model_validate(analysis_data)
                if analysis_data is not None
                else None
            ),
            refinement_result=(
                RefinementResult.model_validate(refinement_data)
                if refinement_data is not None
                else None
            ),
            created_at=self._parse_required_datetime(str(row["created_at"])),
            completed_at=self._parse_required_datetime(str(row["completed_at"])),
            archived_at=self._parse_datetime(row["archived_at"]),
            updated_at=self._parse_required_datetime(str(row["updated_at"])),
        )

    def _initialize(self) -> None:
        """Ensure the SQLite database and schema exist."""

        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS session_records (
                    session_id TEXT PRIMARY KEY,
                    parent_session_id TEXT,
                    session_kind TEXT NOT NULL DEFAULT 'analysis',
                    original_content TEXT NOT NULL,
                    input_echo TEXT NOT NULL,
                    clarification_count INTEGER NOT NULL,
                    archive_status TEXT NOT NULL,
                    archive_url TEXT,
                    archive_error TEXT,
                    created_at TEXT NOT NULL,
                    completed_at TEXT,
                    archived_at TEXT,
                    updated_at TEXT NOT NULL
                )
                """
            )
            record_columns = self._get_column_names(connection, "session_records")
            if "parent_session_id" not in record_columns:
                connection.execute("ALTER TABLE session_records ADD COLUMN parent_session_id TEXT")
            if "session_kind" not in record_columns:
                connection.execute(
                    "ALTER TABLE session_records "
                    "ADD COLUMN session_kind TEXT NOT NULL DEFAULT 'analysis'"
                )

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS session_snapshots (
                    session_id TEXT PRIMARY KEY,
                    parent_session_id TEXT,
                    session_kind TEXT NOT NULL,
                    archive_title TEXT NOT NULL,
                    original_content TEXT NOT NULL,
                    input_echo TEXT NOT NULL,
                    follow_up_question TEXT,
                    clarifications_json TEXT NOT NULL,
                    assumptions_json TEXT NOT NULL,
                    open_questions_json TEXT NOT NULL,
                    analysis_json TEXT,
                    refinement_json TEXT,
                    created_at TEXT NOT NULL,
                    completed_at TEXT NOT NULL,
                    archived_at TEXT,
                    updated_at TEXT NOT NULL
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        """Open a SQLite connection with row access by column name."""

        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self._db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _record_to_row(self, record: SessionRecord) -> tuple[object, ...]:
        """Convert a session record into SQLite parameters."""

        return (
            record.session_id,
            record.parent_session_id,
            record.session_kind.value,
            record.original_content,
            record.input_echo,
            record.clarification_count,
            record.archive_status.value,
            record.archive_url,
            record.archive_error,
            self._serialize_datetime(record.created_at),
            self._serialize_datetime(record.completed_at),
            self._serialize_datetime(record.archived_at),
            self._serialize_datetime(record.updated_at),
        )

    def _snapshot_to_row(self, snapshot: SessionSnapshot) -> tuple[object, ...]:
        """Convert a session snapshot into SQLite parameters."""

        return (
            snapshot.session_id,
            snapshot.parent_session_id,
            snapshot.session_kind.value,
            snapshot.archive_title,
            snapshot.original_content,
            snapshot.input_echo,
            snapshot.follow_up_question,
            self._to_json([item.model_dump() for item in snapshot.clarifications]),
            self._to_json(snapshot.assumptions),
            self._to_json(snapshot.open_questions),
            self._to_json(
                snapshot.analysis.model_dump() if snapshot.analysis is not None else None
            ),
            self._to_json(
                snapshot.refinement_result.model_dump()
                if snapshot.refinement_result is not None
                else None
            ),
            self._serialize_datetime(snapshot.created_at),
            self._serialize_datetime(snapshot.completed_at),
            self._serialize_datetime(snapshot.archived_at),
            self._serialize_datetime(snapshot.updated_at),
        )

    def _serialize_datetime(self, value: datetime | None) -> str | None:
        """Serialize datetimes to ISO 8601 text."""

        if value is None:
            return None
        return value.isoformat()

    def _parse_datetime(self, value: object) -> datetime | None:
        """Parse optional ISO 8601 text back into datetime."""

        if value is None:
            return None
        return datetime.fromisoformat(str(value))

    def _parse_required_datetime(self, value: str) -> datetime:
        """Parse required ISO 8601 text back into datetime."""

        return datetime.fromisoformat(value)

    def _nullable_text(self, value: object) -> str | None:
        """Normalize nullable text columns."""

        if value is None:
            return None
        return str(value)

    def _normalize_session_id(self, session_id: str) -> str:
        """Normalize and validate a session ID lookup key."""

        normalized = session_id.strip()
        if not normalized:
            raise ValueError("session_id must not be blank.")
        return normalized

    def _to_json(self, value: object) -> str:
        """Serialize JSON payloads with UTF-8-safe text preservation."""

        return json.dumps(value, ensure_ascii=False)

    def _from_json(self, value: str) -> list[object]:
        """Parse JSON arrays from storage."""

        loaded = json.loads(value)
        if not isinstance(loaded, list):
            raise ValueError("Stored JSON value is expected to be a list.")
        return loaded

    def _nullable_json(self, value: object) -> dict[str, object] | None:
        """Parse optional JSON objects from storage."""

        if value is None:
            return None
        loaded = json.loads(str(value))
        if loaded is None:
            return None
        if not isinstance(loaded, dict):
            raise ValueError("Stored JSON value is expected to be an object.")
        return loaded

    def _get_column_names(self, connection: sqlite3.Connection, table_name: str) -> set[str]:
        """Fetch existing column names for one table."""

        rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
        return {str(row["name"]) for row in rows}
