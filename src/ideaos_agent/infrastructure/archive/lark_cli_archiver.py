"""Feishu archive adapter implemented via the local lark-cli command."""

import json
import os
import shutil
import subprocess
from datetime import UTC, datetime

from ideaos_agent.domain.archive import (
    ArchiveDeleteResult,
    ArchiveProbeResult,
    ArchiveResult,
    ArchiveStatus,
    SessionArchivePayload,
    SessionArchiver,
)
from ideaos_agent.infrastructure.archive.feishu_doc_renderer import (
    build_feishu_archive_title,
    render_feishu_archive_xml,
)


class LarkCliSessionArchiver(SessionArchiver):
    """Create and delete Feishu Docx archive documents through lark-cli."""

    def __init__(
        self,
        *,
        command: str = "lark-cli",
        archive_as: str = "user",
        parent_token: str = "",
        timeout_seconds: float = 30.0,
    ) -> None:
        self._command = command
        self._archive_as = archive_as
        self._parent_token = parent_token.strip()
        self._timeout_seconds = timeout_seconds

    def archive_session(self, payload: SessionArchivePayload) -> ArchiveResult:
        """Archive one completed session as a new Feishu Docx document."""

        archived_at = datetime.now(UTC)
        title = build_feishu_archive_title(payload)
        xml_content = render_feishu_archive_xml(payload, generated_at=archived_at)

        try:
            completed = self._run_command(
                self._build_create_command(),
                input_text=xml_content,
            )
        except subprocess.TimeoutExpired:
            return ArchiveResult(
                archive_status=ArchiveStatus.FAILED,
                archive_url=None,
                archive_error="Feishu archive request timed out.",
                archived_at=archived_at,
            )
        except OSError as exc:
            return ArchiveResult(
                archive_status=ArchiveStatus.FAILED,
                archive_url=None,
                archive_error=f"Feishu archive command is unavailable: {exc}",
                archived_at=archived_at,
            )

        if completed.returncode != 0:
            return ArchiveResult(
                archive_status=ArchiveStatus.FAILED,
                archive_url=None,
                archive_error=self._extract_error_message(completed.stderr, completed.stdout),
                archived_at=archived_at,
            )

        payload_json = self._parse_json_output(completed.stdout)
        if payload_json is None:
            return ArchiveResult(
                archive_status=ArchiveStatus.FAILED,
                archive_url=None,
                archive_error="Feishu archive returned unreadable JSON.",
                archived_at=archived_at,
            )

        if payload_json.get("ok") is not True:
            return ArchiveResult(
                archive_status=ArchiveStatus.FAILED,
                archive_url=None,
                archive_error=self._extract_error_message_from_json(payload_json),
                archived_at=archived_at,
            )

        document_url = self._extract_document_url(payload_json)
        if document_url is None:
            return ArchiveResult(
                archive_status=ArchiveStatus.FAILED,
                archive_url=None,
                archive_error=(
                    "Feishu archive succeeded but did not return a document URL: "
                    f"{title}"
                ),
                archived_at=archived_at,
            )

        return ArchiveResult(
            archive_status=ArchiveStatus.SUCCEEDED,
            archive_url=document_url,
            archive_error=None,
            archived_at=archived_at,
        )

    def delete_archive(self, archive_url: str) -> ArchiveDeleteResult:
        """Delete one archived Feishu document via drive inspect + delete."""

        normalized_url = archive_url.strip()
        probe_result, target = self._inspect_archive_target(normalized_url)
        if probe_result.found is False:
            return ArchiveDeleteResult(
                archive_url=normalized_url,
                deleted=True,
                archive_error=None,
            )
        if probe_result.found is None:
            return ArchiveDeleteResult(
                archive_url=normalized_url,
                deleted=False,
                archive_error=probe_result.archive_error or "Feishu archive inspect failed.",
            )
        if target is None:
            return ArchiveDeleteResult(
                archive_url=normalized_url,
                deleted=False,
                archive_error="Feishu archive inspect did not return a deletable token/type.",
            )

        try:
            delete_completed = self._run_command(
                self._build_delete_command(
                    file_token=target["token"],
                    file_type=target["type"],
                )
            )
        except subprocess.TimeoutExpired:
            return ArchiveDeleteResult(
                archive_url=normalized_url,
                deleted=False,
                archive_error="Feishu archive delete timed out.",
            )
        except OSError as exc:
            return ArchiveDeleteResult(
                archive_url=normalized_url,
                deleted=False,
                archive_error=f"Feishu archive delete command is unavailable: {exc}",
            )

        if delete_completed.returncode != 0:
            delete_error = self._extract_error_message(
                delete_completed.stderr,
                delete_completed.stdout,
            )
            if self._is_missing_remote_message(delete_error):
                return ArchiveDeleteResult(
                    archive_url=normalized_url,
                    deleted=True,
                    archive_error=None,
                )
            return ArchiveDeleteResult(
                archive_url=normalized_url,
                deleted=False,
                archive_error=delete_error,
            )

        delete_payload = self._parse_json_output(delete_completed.stdout)
        if delete_payload is None:
            return ArchiveDeleteResult(
                archive_url=normalized_url,
                deleted=False,
                archive_error="Feishu archive delete returned unreadable JSON.",
            )

        if delete_payload.get("ok") is False:
            delete_error = self._extract_error_message_from_json(delete_payload)
            if self._is_missing_remote_message(delete_error):
                return ArchiveDeleteResult(
                    archive_url=normalized_url,
                    deleted=True,
                    archive_error=None,
                )
            return ArchiveDeleteResult(
                archive_url=normalized_url,
                deleted=False,
                archive_error=delete_error,
            )

        return ArchiveDeleteResult(
            archive_url=normalized_url,
            deleted=True,
            archive_error=None,
        )

    def probe_archive(self, archive_url: str) -> ArchiveProbeResult:
        """Probe whether one archived Feishu document is still present remotely."""

        normalized_url = archive_url.strip()
        try:
            fetch_completed = self._run_command(self._build_fetch_command(normalized_url))
        except subprocess.TimeoutExpired:
            return ArchiveProbeResult(
                archive_url=normalized_url,
                found=None,
                archive_error="Feishu archive fetch probe timed out.",
            )
        except OSError as exc:
            return ArchiveProbeResult(
                archive_url=normalized_url,
                found=None,
                archive_error=f"Feishu archive fetch command is unavailable: {exc}",
            )

        if fetch_completed.returncode != 0:
            fetch_error = self._extract_error_message(
                fetch_completed.stderr,
                fetch_completed.stdout,
            )
            if self._is_missing_remote_message(fetch_error):
                return ArchiveProbeResult(
                    archive_url=normalized_url,
                    found=False,
                    archive_error=None,
                )
            return ArchiveProbeResult(
                archive_url=normalized_url,
                found=None,
                archive_error=fetch_error,
            )

        fetch_payload = self._parse_json_output(fetch_completed.stdout)
        if fetch_payload is None:
            return ArchiveProbeResult(
                archive_url=normalized_url,
                found=None,
                archive_error="Feishu archive fetch probe returned unreadable JSON.",
            )

        if fetch_payload.get("ok") is False:
            fetch_error = self._extract_error_message_from_json(fetch_payload)
            if self._is_missing_remote_message(fetch_error):
                return ArchiveProbeResult(
                    archive_url=normalized_url,
                    found=False,
                    archive_error=None,
                )
            return ArchiveProbeResult(
                archive_url=normalized_url,
                found=None,
                archive_error=fetch_error,
            )

        if not self._has_fetched_document(fetch_payload):
            return ArchiveProbeResult(
                archive_url=normalized_url,
                found=None,
                archive_error="Feishu archive fetch probe did not return document data.",
            )

        return ArchiveProbeResult(
            archive_url=normalized_url,
            found=True,
            archive_error=None,
        )

    def _build_create_command(self) -> list[str]:
        """Build the lark-cli command for document creation."""

        command_path = self._resolve_command_path()
        command = [
            command_path,
            "docs",
            "+create",
            "--as",
            self._archive_as,
            "--json",
            "--content",
            "-",
        ]
        if self._parent_token:
            command.extend(["--parent-token", self._parent_token])
        return command

    def _build_inspect_command(self, archive_url: str) -> list[str]:
        """Build the lark-cli command that resolves URL to canonical token/type."""

        return [
            self._resolve_command_path(),
            "drive",
            "+inspect",
            "--as",
            self._archive_as,
            "--json",
            "--url",
            archive_url,
        ]

    def _build_fetch_command(self, archive_url: str) -> list[str]:
        """Build the lightweight docs fetch command used for archive presence probes."""

        return [
            self._resolve_command_path(),
            "docs",
            "+fetch",
            "--as",
            self._archive_as,
            "--json",
            "--doc",
            archive_url,
            "--scope",
            "outline",
            "--max-depth",
            "1",
        ]

    def _build_delete_command(self, *, file_token: str, file_type: str) -> list[str]:
        """Build the lark-cli command that deletes one archived file."""

        return [
            self._resolve_command_path(),
            "drive",
            "+delete",
            "--as",
            self._archive_as,
            "--json",
            "--file-token",
            file_token,
            "--type",
            file_type,
            "--yes",
        ]

    def _inspect_archive_target(
        self,
        archive_url: str,
    ) -> tuple[ArchiveProbeResult, dict[str, str] | None]:
        """Inspect one archive URL and resolve its canonical token/type when possible."""

        normalized_url = archive_url.strip()
        try:
            inspect_completed = self._run_command(self._build_inspect_command(normalized_url))
        except subprocess.TimeoutExpired:
            return (
                ArchiveProbeResult(
                    archive_url=normalized_url,
                    found=None,
                    archive_error="Feishu archive inspect timed out.",
                ),
                None,
            )
        except OSError as exc:
            return (
                ArchiveProbeResult(
                    archive_url=normalized_url,
                    found=None,
                    archive_error=f"Feishu archive inspect command is unavailable: {exc}",
                ),
                None,
            )

        if inspect_completed.returncode != 0:
            inspect_error = self._extract_error_message(
                inspect_completed.stderr,
                inspect_completed.stdout,
            )
            if self._is_missing_remote_message(inspect_error):
                return (
                    ArchiveProbeResult(
                        archive_url=normalized_url,
                        found=False,
                        archive_error=None,
                    ),
                    None,
                )
            return (
                ArchiveProbeResult(
                    archive_url=normalized_url,
                    found=None,
                    archive_error=inspect_error,
                ),
                None,
            )

        inspect_payload = self._parse_json_output(inspect_completed.stdout)
        if inspect_payload is None:
            return (
                ArchiveProbeResult(
                    archive_url=normalized_url,
                    found=None,
                    archive_error="Feishu archive inspect returned unreadable JSON.",
                ),
                None,
            )

        if inspect_payload.get("ok") is False:
            inspect_error = self._extract_error_message_from_json(inspect_payload)
            if self._is_missing_remote_message(inspect_error):
                return (
                    ArchiveProbeResult(
                        archive_url=normalized_url,
                        found=False,
                        archive_error=None,
                    ),
                    None,
                )
            return (
                ArchiveProbeResult(
                    archive_url=normalized_url,
                    found=None,
                    archive_error=inspect_error,
                ),
                None,
            )

        target = self._extract_drive_target(inspect_payload)
        if target is None:
            return (
                ArchiveProbeResult(
                    archive_url=normalized_url,
                    found=None,
                    archive_error="Feishu archive inspect did not return a canonical token/type.",
                ),
                None,
            )

        return (
            ArchiveProbeResult(
                archive_url=normalized_url,
                found=True,
                archive_error=None,
            ),
            target,
        )

    def _resolve_command_path(self) -> str:
        """Resolve the configured CLI command into an executable path when possible."""

        resolved = shutil.which(self._command)
        if resolved is not None:
            return resolved
        return self._command

    def _build_command_env(self) -> dict[str, str]:
        """Build a clean environment for stable machine-readable CLI output."""

        env = os.environ.copy()
        env["LARKSUITE_CLI_NO_UPDATE_NOTIFIER"] = "1"
        env["LARKSUITE_CLI_NO_SKILLS_NOTIFIER"] = "1"
        return env

    def _run_command(
        self,
        command: list[str],
        *,
        input_text: str | None = None,
    ) -> subprocess.CompletedProcess[str]:
        """Run one CLI command with shared machine-readable settings."""

        return subprocess.run(
            command,
            input=input_text,
            text=True,
            encoding="utf-8",
            capture_output=True,
            timeout=self._timeout_seconds,
            env=self._build_command_env(),
            check=False,
        )

    def _parse_json_output(self, raw_output: str) -> dict[str, object] | None:
        """Parse JSON output from lark-cli."""

        try:
            payload = json.loads(raw_output)
        except json.JSONDecodeError:
            return None
        if not isinstance(payload, dict):
            return None
        return payload

    def _extract_document_url(self, payload: dict[str, object]) -> str | None:
        """Extract the created document URL from a successful lark-cli response."""

        data = payload.get("data")
        if not isinstance(data, dict):
            return None
        document = data.get("document")
        if not isinstance(document, dict):
            return None
        url = document.get("url")
        if not isinstance(url, str):
            return None
        normalized = url.strip()
        if not normalized:
            return None
        return normalized

    def _extract_drive_target(self, payload: dict[str, object]) -> dict[str, str] | None:
        """Extract the canonical file token and type from drive +inspect JSON."""

        data = payload.get("data")
        if not isinstance(data, dict):
            return None

        token = data.get("token")
        file_type = data.get("type")
        if not isinstance(token, str) or not token.strip():
            return None
        if not isinstance(file_type, str) or not file_type.strip():
            return None
        return {"token": token.strip(), "type": file_type.strip()}

    def _extract_error_message(self, stderr: str, stdout: str) -> str:
        """Derive a concise archive error message from CLI output."""

        for candidate in (stderr, stdout):
            payload_json = self._parse_json_output(candidate)
            if payload_json is not None:
                return self._extract_error_message_from_json(payload_json)
            normalized = candidate.strip()
            if normalized:
                return normalized
        return "Feishu archive command failed without a readable error message."

    def _extract_error_message_from_json(self, payload: dict[str, object]) -> str:
        """Extract a human-readable error message from a lark-cli JSON payload."""

        error = payload.get("error")
        if isinstance(error, dict):
            message = error.get("message")
            if isinstance(message, str) and message.strip():
                return message.strip()
            hint = error.get("hint")
            if isinstance(hint, str) and hint.strip():
                return hint.strip()
        message = payload.get("message")
        if isinstance(message, str) and message.strip():
            return message.strip()
        return "Feishu archive command did not return a readable error message."

    def _has_fetched_document(self, payload: dict[str, object]) -> bool:
        """Check whether docs +fetch returned the expected document payload."""

        data = payload.get("data")
        if not isinstance(data, dict):
            return False
        document = data.get("document")
        return isinstance(document, dict)

    def _is_missing_remote_message(self, message: str) -> bool:
        """Treat missing or already-deleted remote documents as absent."""

        normalized = message.strip().lower()
        if not normalized:
            return False
        return any(
            marker in normalized
            for marker in (
                "not found",
                "not exist",
                "not_exist",
                "resource not found",
                "has been deleted",
                "page has been deleted",
                "can no longer be edited",
                "404",
            )
        )
