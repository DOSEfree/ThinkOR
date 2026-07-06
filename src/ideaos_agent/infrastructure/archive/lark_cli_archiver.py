"""Feishu archive adapter implemented via the local lark-cli command."""

import json
import os
import shutil
import subprocess
from datetime import UTC, datetime

from ideaos_agent.domain.archive import (
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
    """Create Feishu Docx archive documents through lark-cli."""

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
        command = self._build_command()

        try:
            completed = subprocess.run(
                command,
                input=xml_content,
                text=True,
                encoding="utf-8",
                capture_output=True,
                timeout=self._timeout_seconds,
                env=self._build_command_env(),
                check=False,
            )
        except subprocess.TimeoutExpired:
            return ArchiveResult(
                archive_status=ArchiveStatus.FAILED,
                archive_url=None,
                archive_error="飞书归档超时。",
                archived_at=archived_at,
            )
        except OSError as exc:
            return ArchiveResult(
                archive_status=ArchiveStatus.FAILED,
                archive_url=None,
                archive_error=f"飞书归档命令不可用：{exc}",
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
                archive_error="飞书归档返回无法解析的 JSON。",
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
                archive_error=f"飞书归档创建成功但未返回文档链接：{title}",
                archived_at=archived_at,
            )

        return ArchiveResult(
            archive_status=ArchiveStatus.SUCCEEDED,
            archive_url=document_url,
            archive_error=None,
            archived_at=archived_at,
        )

    def _build_command(self) -> list[str]:
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

    def _extract_error_message(self, stderr: str, stdout: str) -> str:
        """Derive a concise archive error message from CLI output."""

        for candidate in (stderr, stdout):
            payload_json = self._parse_json_output(candidate)
            if payload_json is not None:
                return self._extract_error_message_from_json(payload_json)
            normalized = candidate.strip()
            if normalized:
                return normalized
        return "飞书归档失败，未返回可读错误信息。"

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
        return "飞书归档失败，CLI 未返回明确错误信息。"
