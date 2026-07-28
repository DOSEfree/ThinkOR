"""Safe status checks and user-auth flows for the local lark-cli executable."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

LarkCliAvailability = Literal[
    "cli_missing",
    "cli_unresponsive",
    "unauthenticated",
    "authenticated_unverified",
    "identity_mismatch",
]


@dataclass(frozen=True)
class LarkCliStatus:
    """Public, non-secret summary of the local lark-cli readiness."""

    availability: LarkCliAvailability
    identity: Literal["user", "bot", "unknown"]
    version: str | None
    next_step: str
    update_available: bool = False


@dataclass(frozen=True)
class LarkAuthorizationStart:
    """Ephemeral values needed only until a user authorization is completed."""

    verification_url: str
    device_code: str


class LarkCliStatusAdapter:
    """Run fixed lark-cli status commands without exposing their raw output."""

    def __init__(self, *, command: str, archive_as: str, timeout_seconds: float) -> None:
        self._command = command
        self._archive_as = archive_as
        self._timeout_seconds = timeout_seconds

    def inspect(self) -> LarkCliStatus:
        """Check executable, token validity, and selected archive identity."""

        command_path = shutil.which(self._command)
        if command_path is None:
            return LarkCliStatus(
                availability="cli_missing",
                identity="unknown",
                version=None,
                next_step="install_cli",
            )

        version = self._read_version(command_path)
        if version is None:
            return LarkCliStatus(
                availability="cli_unresponsive",
                identity="unknown",
                version=None,
                next_step="retry_cli_check",
            )

        completed = self._run([command_path, "auth", "status", "--json", "--verify"])
        raw_payload = completed.stdout if completed.returncode == 0 else completed.stderr
        payload = self._parse_json(raw_payload)
        if payload is None:
            return LarkCliStatus(
                availability="unauthenticated",
                identity="unknown",
                version=version,
                next_step="authorize_user" if self._archive_as == "user" else "configure_bot",
            )

        selected_identity = self._selected_identity_status(payload)
        if selected_identity == self._archive_as:
            return LarkCliStatus(
                availability="authenticated_unverified",
                identity=selected_identity,
                version=version,
                next_step="try_archive",
            )
        if selected_identity in {"user", "bot"}:
            return LarkCliStatus(
                availability="identity_mismatch",
                identity=selected_identity,
                version=version,
                next_step="configure_selected_identity",
            )
        return LarkCliStatus(
            availability="unauthenticated",
            identity="unknown",
            version=version,
            next_step="authorize_user" if self._archive_as == "user" else "configure_bot",
        )

    def check_update(self) -> bool:
        """Return whether CLI reports an update without performing any update."""

        command_path = shutil.which(self._command)
        if command_path is None:
            return False
        completed = self._run([command_path, "update", "--check", "--json"])
        payload = self._parse_json(completed.stdout)
        if payload is None:
            return False
        notice = payload.get("_notice")
        return isinstance(notice, dict) and isinstance(notice.get("update"), dict)

    def start_user_authorization(self) -> LarkAuthorizationStart:
        """Start a new user OAuth flow; callers must keep the device code in memory only."""

        command_path = self._require_command()
        completed = self._run(
            [
                command_path,
                "auth",
                "login",
                "--domain",
                "docs",
                "--domain",
                "drive",
                "--no-wait",
                "--json",
            ]
        )
        payload = self._parse_json(completed.stdout)
        if completed.returncode != 0 or payload is None or payload.get("ok") is not True:
            raise RuntimeError("Unable to start Feishu user authorization.")
        data = payload.get("data")
        if not isinstance(data, dict):
            raise RuntimeError("Feishu authorization did not return a verification flow.")
        verification_url = data.get("verification_url")
        device_code = data.get("device_code")
        if not isinstance(verification_url, str) or not verification_url:
            raise RuntimeError("Feishu authorization did not return a verification URL.")
        if not isinstance(device_code, str) or not device_code:
            raise RuntimeError("Feishu authorization did not return a device code.")
        return LarkAuthorizationStart(verification_url=verification_url, device_code=device_code)

    def render_qrcode(
        self,
        *,
        verification_url: str,
        output_path: Path,
        project_root: Path,
    ) -> None:
        """Ask lark-cli to render an authorization URL into a controlled PNG path."""

        command_path = self._require_command()
        try:
            relative_path = output_path.relative_to(project_root)
        except ValueError as exc:
            raise RuntimeError("QR code output must remain inside the project directory.") from exc
        completed = self._run(
            [
                command_path,
                "auth",
                "qrcode",
                verification_url,
                "--output",
                str(relative_path),
            ],
            cwd=project_root,
        )
        if completed.returncode != 0 or not output_path.is_file():
            raise RuntimeError("Unable to render the Feishu authorization QR code.")

    def complete_user_authorization(self, *, device_code: str) -> None:
        """Finish an existing in-memory user authorization flow."""

        command_path = self._require_command()
        completed = self._run(
            [command_path, "auth", "login", "--device-code", device_code]
        )
        if completed.returncode != 0:
            raise RuntimeError("Feishu user authorization was not completed.")

    def _require_command(self) -> str:
        command_path = shutil.which(self._command)
        if command_path is None:
            raise RuntimeError("The configured Feishu CLI command is unavailable.")
        return command_path

    def _read_version(self, command_path: str) -> str | None:
        completed = self._run([command_path, "--version"])
        if completed.returncode != 0:
            return None
        version = completed.stdout.strip().splitlines()
        return version[0][:80] if version else None

    def _selected_identity_status(
        self,
        payload: dict[str, object],
    ) -> Literal["user", "bot", "unknown"]:
        """Resolve readiness from auth status rather than its active-default identity."""

        identities = payload.get("identities")
        if isinstance(identities, dict):
            selected = identities.get(self._archive_as)
            if self._identity_is_ready(selected):
                return self._normalize_identity(self._archive_as)

            for identity in ("user", "bot"):
                if (
                    identity != self._archive_as
                    and self._identity_is_ready(identities.get(identity))
                ):
                    return self._normalize_identity(identity)
            return "unknown"

        # Older CLI releases use a conventional {"ok": true, "identity": ...} envelope.
        if payload.get("ok") is True:
            return self._normalize_identity(payload.get("identity"))
        return "unknown"

    @staticmethod
    def _identity_is_ready(value: object) -> bool:
        return (
            isinstance(value, dict)
            and value.get("status") == "ready"
            and value.get("verified") is not False
        )

    @staticmethod
    def _normalize_identity(value: object) -> Literal["user", "bot", "unknown"]:
        if value == "user":
            return "user"
        if value == "bot":
            return "bot"
        return "unknown"

    def _run(
        self,
        command: list[str],
        *,
        cwd: Path | None = None,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            command,
            capture_output=True,
            check=False,
            cwd=cwd,
            encoding="utf-8",
            env={
                **os.environ,
                "LARKSUITE_CLI_NO_UPDATE_NOTIFIER": "1",
                "LARKSUITE_CLI_NO_SKILLS_NOTIFIER": "1",
            },
            text=True,
            timeout=self._timeout_seconds,
        )

    @staticmethod
    def _parse_json(raw: str) -> dict[str, object] | None:
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            return None
        return value if isinstance(value, dict) else None
