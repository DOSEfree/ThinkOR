"""SQLite-backed minimal session archive index storage."""

import sqlite3
from datetime import datetime
from pathlib import Path

from ideaos_agent.domain.archive import ArchiveStatus, SessionArchiveStore, SessionRecord


class SqliteSessionArchiveStore(SessionArchiveStore):
    """Persist minimal session archive records in a local SQLite database."""

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = Path(db_path)
        self._initialize()

    def save_session_record(self, record: SessionRecord) -> SessionRecord:
        """Create or update a session record while preserving first-created time."""

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
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    self._record_to_row(persisted_record),
                )
            else:
                connection.execute(
                    """
                    UPDATE session_records
                    SET
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
            raise RuntimeError("SQLite 会话记录保存后未能重新读取。")
        return saved_record

    def get_session_record(self, session_id: str) -> SessionRecord | None:
        """Fetch a session record by ID."""

        normalized_session_id = session_id.strip()
        if not normalized_session_id:
            raise ValueError("session_id 不能为空白。")

        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    session_id,
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

    def _initialize(self) -> None:
        """Ensure the SQLite database and schema exist."""

        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS session_records (
                    session_id TEXT PRIMARY KEY,
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

    def _connect(self) -> sqlite3.Connection:
        """Open a SQLite connection with row access by column name."""

        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self._db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _record_to_row(self, record: SessionRecord) -> tuple[object, ...]:
        """Convert a session record into a SQLite parameter tuple."""

        return (
            record.session_id,
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

    def _serialize_datetime(self, value: datetime | None) -> str | None:
        """Serialize datetimes to ISO 8601 text for SQLite storage."""

        if value is None:
            return None
        return value.isoformat()

    def _parse_datetime(self, value: str | None) -> datetime | None:
        """Parse ISO 8601 text from SQLite back into datetime objects."""

        if value is None:
            return None
        return datetime.fromisoformat(value)

    def _parse_required_datetime(self, value: str) -> datetime:
        """Parse a required ISO 8601 text value from SQLite."""

        return datetime.fromisoformat(value)

    def _nullable_text(self, value: object) -> str | None:
        """Normalize SQLite nullable text columns."""

        if value is None:
            return None
        return str(value)
