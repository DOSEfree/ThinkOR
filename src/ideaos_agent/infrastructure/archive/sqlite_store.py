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
            update_payload: dict[str, object] = {"created_at": existing.created_at}
            if (
                record.formal_version_number is None
                and existing.formal_version_number is not None
            ):
                update_payload["formal_version_number"] = existing.formal_version_number
            persisted_record = record.model_copy(update=update_payload)

        with self._connect() as connection:
            if existing is None:
                connection.execute(
                    """
                    INSERT INTO session_records (
                        session_id,
                        root_session_id,
                        parent_session_id,
                        session_kind,
                        formal_version_number,
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
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    self._record_to_row(persisted_record),
                )
            else:
                connection.execute(
                    """
                    UPDATE session_records
                    SET
                        root_session_id = ?,
                        parent_session_id = ?,
                        session_kind = ?,
                        formal_version_number = ?,
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
                        persisted_record.root_session_id,
                        persisted_record.parent_session_id,
                        persisted_record.session_kind.value,
                        persisted_record.formal_version_number,
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
                    root_session_id,
                    parent_session_id,
                    session_kind,
                    formal_version_number,
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
            root_session_id=self._resolve_root_session_id(
                session_id=str(row["session_id"]),
                session_kind=SessionKind(str(row["session_kind"])),
                stored_root_session_id=row["root_session_id"],
            ),
            parent_session_id=self._nullable_text(row["parent_session_id"]),
            session_kind=SessionKind(str(row["session_kind"])),
            formal_version_number=self._nullable_int(row["formal_version_number"]),
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

    def list_session_records(
        self,
        *,
        limit: int | None = None,
        root_session_id: str | None = None,
        session_kind: SessionKind | None = None,
    ) -> list[SessionRecord]:
        """List session index records for history and thread queries."""

        sql = """
            SELECT
                session_id,
                root_session_id,
                parent_session_id,
                session_kind,
                formal_version_number,
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
        """
        conditions: list[str] = []
        parameters: list[object] = []
        if root_session_id is not None:
            conditions.append("root_session_id = ?")
            parameters.append(self._normalize_session_id(root_session_id))
        if session_kind is not None:
            conditions.append("session_kind = ?")
            parameters.append(session_kind.value)
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY updated_at DESC"
        if limit is not None:
            sql += " LIMIT ?"
            parameters.append(self._normalize_positive_limit(limit))

        with self._connect() as connection:
            rows = connection.execute(sql, tuple(parameters)).fetchall()

        return [self._row_to_session_record(row) for row in rows]

    def delete_session_records(self, *, root_session_id: str) -> int:
        """Delete all session index records for one thread."""

        normalized_root_session_id = self._normalize_session_id(root_session_id)
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM session_records WHERE root_session_id = ?",
                (normalized_root_session_id,),
            )
        return int(cursor.rowcount)

    def delete_session_record(self, session_id: str) -> bool:
        """Delete one session index record by ID."""

        normalized_session_id = self._normalize_session_id(session_id)
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM session_records WHERE session_id = ?",
                (normalized_session_id,),
            )
        return int(cursor.rowcount) > 0

    def save_session_snapshot(self, snapshot: SessionSnapshot) -> SessionSnapshot:
        """Create or update a structured session snapshot while preserving created_at."""

        existing = self.get_session_snapshot(snapshot.session_id)
        persisted_snapshot = snapshot
        if existing is not None:
            update_payload: dict[str, object] = {"created_at": existing.created_at}
            if (
                snapshot.formal_version_number is None
                and existing.formal_version_number is not None
            ):
                update_payload["formal_version_number"] = existing.formal_version_number
            persisted_snapshot = snapshot.model_copy(update=update_payload)

        with self._connect() as connection:
            if existing is None:
                connection.execute(
                    """
                    INSERT INTO session_snapshots (
                        session_id,
                        root_session_id,
                        parent_session_id,
                        session_kind,
                        formal_version_number,
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
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    self._snapshot_to_row(persisted_snapshot),
                )
            else:
                connection.execute(
                    """
                    UPDATE session_snapshots
                    SET
                        root_session_id = ?,
                        parent_session_id = ?,
                        session_kind = ?,
                        formal_version_number = ?,
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
                        persisted_snapshot.root_session_id,
                        persisted_snapshot.parent_session_id,
                        persisted_snapshot.session_kind.value,
                        persisted_snapshot.formal_version_number,
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
                    root_session_id,
                    parent_session_id,
                    session_kind,
                    formal_version_number,
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

        return self._row_to_session_snapshot(
            row,
            clarifications_data=clarifications_data,
            assumptions_data=assumptions_data,
            open_questions_data=open_questions_data,
            analysis_data=analysis_data,
            refinement_data=refinement_data,
        )

    def list_session_snapshots(
        self,
        *,
        limit: int | None = None,
        root_session_id: str | None = None,
        session_kind: SessionKind | None = None,
    ) -> list[SessionSnapshot]:
        """List structured session snapshots for history and thread queries."""

        sql = """
            SELECT
                session_id,
                root_session_id,
                parent_session_id,
                session_kind,
                formal_version_number,
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
        """
        conditions: list[str] = []
        parameters: list[object] = []
        if root_session_id is not None:
            conditions.append("root_session_id = ?")
            parameters.append(self._normalize_session_id(root_session_id))
        if session_kind is not None:
            conditions.append("session_kind = ?")
            parameters.append(session_kind.value)
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY updated_at DESC"
        if limit is not None:
            sql += " LIMIT ?"
            parameters.append(self._normalize_positive_limit(limit))

        with self._connect() as connection:
            rows = connection.execute(sql, tuple(parameters)).fetchall()

        snapshots: list[SessionSnapshot] = []
        for row in rows:
            snapshots.append(
                self._row_to_session_snapshot(
                    row,
                    clarifications_data=self._from_json(str(row["clarifications_json"])),
                    assumptions_data=self._from_json(str(row["assumptions_json"])),
                    open_questions_data=self._from_json(str(row["open_questions_json"])),
                    analysis_data=self._nullable_json(row["analysis_json"]),
                    refinement_data=self._nullable_json(row["refinement_json"]),
                )
            )
        return snapshots

    def delete_session_snapshots(self, *, root_session_id: str) -> int:
        """Delete all structured session snapshots for one thread."""

        normalized_root_session_id = self._normalize_session_id(root_session_id)
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM session_snapshots WHERE root_session_id = ?",
                (normalized_root_session_id,),
            )
        return int(cursor.rowcount)

    def delete_session_snapshot(self, session_id: str) -> bool:
        """Delete one structured session snapshot by ID."""

        normalized_session_id = self._normalize_session_id(session_id)
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM session_snapshots WHERE session_id = ?",
                (normalized_session_id,),
            )
        return int(cursor.rowcount) > 0

    def _initialize(self) -> None:
        """Ensure the SQLite database and schema exist."""

        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS session_records (
                    session_id TEXT PRIMARY KEY,
                    root_session_id TEXT NOT NULL DEFAULT '',
                    parent_session_id TEXT,
                    session_kind TEXT NOT NULL DEFAULT 'analysis',
                    formal_version_number INTEGER,
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
            if "root_session_id" not in record_columns:
                connection.execute(
                    "ALTER TABLE session_records "
                    "ADD COLUMN root_session_id TEXT NOT NULL DEFAULT ''"
                )
            if "formal_version_number" not in record_columns:
                connection.execute(
                    "ALTER TABLE session_records ADD COLUMN formal_version_number INTEGER"
                )
            self._migrate_legacy_fake_archive_urls(connection)

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS session_snapshots (
                    session_id TEXT PRIMARY KEY,
                    root_session_id TEXT NOT NULL DEFAULT '',
                    parent_session_id TEXT,
                    session_kind TEXT NOT NULL,
                    formal_version_number INTEGER,
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
            snapshot_columns = self._get_column_names(connection, "session_snapshots")
            if "root_session_id" not in snapshot_columns:
                connection.execute(
                    "ALTER TABLE session_snapshots "
                    "ADD COLUMN root_session_id TEXT NOT NULL DEFAULT ''"
                )
            if "formal_version_number" not in snapshot_columns:
                connection.execute(
                    "ALTER TABLE session_snapshots ADD COLUMN formal_version_number INTEGER"
                )
            self._backfill_formal_version_numbers(connection)

    @staticmethod
    def _migrate_legacy_fake_archive_urls(connection: sqlite3.Connection) -> None:
        """Clear v0.6 fake URLs so they cannot be mistaken for real Feishu documents."""

        connection.execute(
            """
            UPDATE session_records
            SET archive_status = ?, archive_url = NULL, archive_error = NULL
            WHERE archive_status = ?
              AND archive_url LIKE ?
            """,
            (
                ArchiveStatus.SIMULATED.value,
                ArchiveStatus.SUCCEEDED.value,
                "https://feishu.example.com/docx/%",
            ),
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
            record.root_session_id,
            record.parent_session_id,
            record.session_kind.value,
            record.formal_version_number,
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

    def _row_to_session_record(self, row: sqlite3.Row) -> SessionRecord:
        """Convert one SQLite row into a session record model."""

        session_kind = SessionKind(str(row["session_kind"]))
        session_id = str(row["session_id"])
        return SessionRecord(
            session_id=session_id,
            root_session_id=self._resolve_root_session_id(
                session_id=session_id,
                session_kind=session_kind,
                stored_root_session_id=row["root_session_id"],
            ),
            parent_session_id=self._nullable_text(row["parent_session_id"]),
            session_kind=session_kind,
            formal_version_number=self._nullable_int(row["formal_version_number"]),
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

    def _snapshot_to_row(self, snapshot: SessionSnapshot) -> tuple[object, ...]:
        """Convert a session snapshot into SQLite parameters."""

        return (
            snapshot.session_id,
            snapshot.root_session_id,
            snapshot.parent_session_id,
            snapshot.session_kind.value,
            snapshot.formal_version_number,
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

    def _row_to_session_snapshot(
        self,
        row: sqlite3.Row,
        *,
        clarifications_data: list[object],
        assumptions_data: list[object],
        open_questions_data: list[object],
        analysis_data: dict[str, object] | None,
        refinement_data: dict[str, object] | None,
    ) -> SessionSnapshot:
        """Convert one SQLite row into a structured session snapshot."""

        session_kind = SessionKind(str(row["session_kind"]))
        session_id = str(row["session_id"])
        return SessionSnapshot(
            session_id=session_id,
            root_session_id=self._resolve_root_session_id(
                session_id=session_id,
                session_kind=session_kind,
                stored_root_session_id=row["root_session_id"],
            ),
            parent_session_id=self._nullable_text(row["parent_session_id"]),
            session_kind=session_kind,
            formal_version_number=self._nullable_int(row["formal_version_number"]),
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

    def _nullable_int(self, value: object) -> int | None:
        """Normalize nullable integer columns."""

        if value is None:
            return None
        if isinstance(value, int):
            return value
        return int(str(value))

    def _backfill_formal_version_numbers(self, connection: sqlite3.Connection) -> None:
        """Assign stable formal version numbers to legacy formal rows that predate v0.4.5."""

        self._backfill_formal_version_numbers_for_table(connection, "session_records")
        self._backfill_formal_version_numbers_for_table(connection, "session_snapshots")

    def _backfill_formal_version_numbers_for_table(
        self,
        connection: sqlite3.Connection,
        table_name: str,
    ) -> None:
        """Backfill missing formal version numbers for one SQLite table."""

        rows = connection.execute(
            f"""
            SELECT
                session_id,
                root_session_id,
                session_kind,
                formal_version_number,
                created_at
            FROM {table_name}
            WHERE session_kind IN ('analysis', 'full_plan_composed')
            ORDER BY root_session_id ASC, created_at ASC, session_id ASC
            """
        ).fetchall()

        grouped_rows: dict[str, list[sqlite3.Row]] = {}
        for row in rows:
            root_session_id = str(row["root_session_id"] or row["session_id"])
            grouped_rows.setdefault(root_session_id, []).append(row)

        for thread_rows in grouped_rows.values():
            used_numbers = {
                int(row["formal_version_number"])
                for row in thread_rows
                if row["formal_version_number"] is not None
            }
            next_number = 1
            for row in thread_rows:
                if row["formal_version_number"] is not None:
                    continue
                while next_number in used_numbers:
                    next_number += 1
                connection.execute(
                    f"UPDATE {table_name} SET formal_version_number = ? WHERE session_id = ?",
                    (next_number, str(row["session_id"])),
                )
                used_numbers.add(next_number)
                next_number += 1

    def _resolve_root_session_id(
        self,
        *,
        session_id: str,
        session_kind: SessionKind,
        stored_root_session_id: object,
    ) -> str:
        """Resolve a compatible root session ID for new and old SQLite rows."""

        resolved = self._nullable_text(stored_root_session_id)
        if resolved is not None and resolved.strip():
            return resolved

        # Backward compatibility for v0.2.x rows written before root_session_id existed.
        if session_kind == SessionKind.ANALYSIS:
            return session_id
        return session_id

    def _normalize_session_id(self, session_id: str) -> str:
        """Normalize and validate a session ID lookup key."""

        normalized = session_id.strip()
        if not normalized:
            raise ValueError("session_id must not be blank.")
        return normalized

    def _normalize_positive_limit(self, limit: int) -> int:
        """Normalize list limits used by history queries."""

        if limit <= 0:
            raise ValueError("limit must be positive.")
        return limit

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
