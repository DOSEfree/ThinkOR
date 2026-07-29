"""Short-lived, non-persistent orchestration for Feishu user authorization."""

from __future__ import annotations

import re
import secrets
import subprocess
import threading
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from ideaos_agent.infrastructure.archive.lark_cli_status import LarkCliStatus, LarkCliStatusAdapter


@dataclass(frozen=True)
class LarkSetupFlowView:
    """Public details for one active browser authorization flow."""

    flow_id: str
    verification_url: str
    expires_at: datetime


@dataclass
class _LarkSetupFlow:
    device_code: str
    verification_url: str
    expires_at: datetime
    qr_code_path: Path


@dataclass
class _LarkConfigurationFlow:
    process: subprocess.Popen[str]
    expires_at: datetime
    qr_code_path: Path
    status: str = "starting"
    verification_url: str | None = None


@dataclass(frozen=True)
class LarkConfigurationFlowView:
    """Public, non-secret progress for one CLI application setup flow."""

    flow_id: str
    status: str
    verification_url: str | None


class LarkSetupService:
    """Keep device codes only in process memory for one short authorization flow."""

    def __init__(self, *, adapter: LarkCliStatusAdapter, project_root: Path) -> None:
        self._adapter = adapter
        self._project_root = project_root
        self._flows: dict[str, _LarkSetupFlow] = {}
        self._configuration_flows: dict[str, _LarkConfigurationFlow] = {}
        self._flow_lock = threading.RLock()

    def recheck(self) -> LarkCliStatus:
        self._cleanup_expired()
        return self._adapter.inspect()

    def start_user_authorization(self) -> LarkSetupFlowView:
        self._cleanup_expired()
        authorization = self._adapter.start_user_authorization()
        flow_id = secrets.token_urlsafe(24)
        expires_at = datetime.now(UTC) + timedelta(minutes=5)
        qr_code_path = self._project_root / "data" / "lark_setup" / f"{flow_id}.png"
        qr_code_path.parent.mkdir(parents=True, exist_ok=True)
        self._adapter.render_qrcode(
            verification_url=authorization.verification_url,
            output_path=qr_code_path,
            project_root=self._project_root,
        )
        self._flows[flow_id] = _LarkSetupFlow(
            device_code=authorization.device_code,
            verification_url=authorization.verification_url,
            expires_at=expires_at,
            qr_code_path=qr_code_path,
        )
        return LarkSetupFlowView(flow_id, authorization.verification_url, expires_at)

    def start_cli_configuration(self) -> LarkConfigurationFlowView:
        """Start the local CLI's browser-based app setup and monitor it in the background."""

        self._cleanup_expired()
        with self._flow_lock:
            for existing_flow_id, existing_flow in self._configuration_flows.items():
                if existing_flow.status in {"starting", "awaiting_browser"}:
                    return LarkConfigurationFlowView(
                        existing_flow_id,
                        existing_flow.status,
                        existing_flow.verification_url,
                    )

        flow_id = secrets.token_urlsafe(24)
        expires_at = datetime.now(UTC) + timedelta(minutes=10)
        qr_code_path = self._project_root / "data" / "lark_setup" / f"{flow_id}.png"
        process = self._adapter.start_cli_configuration()
        with self._flow_lock:
            self._configuration_flows[flow_id] = _LarkConfigurationFlow(
                process=process,
                expires_at=expires_at,
                qr_code_path=qr_code_path,
            )
        threading.Thread(
            target=self._monitor_cli_configuration,
            args=(flow_id,),
            daemon=True,
        ).start()
        return LarkConfigurationFlowView(flow_id, "starting", None)

    def get_cli_configuration(self, flow_id: str) -> LarkConfigurationFlowView | None:
        """Return safe progress for a browser-based CLI application setup."""

        self._cleanup_expired()
        with self._flow_lock:
            flow = self._configuration_flows.get(flow_id)
            if flow is None:
                return None
            return LarkConfigurationFlowView(flow_id, flow.status, flow.verification_url)

    def get_flow(self, flow_id: str) -> LarkSetupFlowView | None:
        self._cleanup_expired()
        flow = self._flows.get(flow_id)
        if flow is None:
            return None
        return LarkSetupFlowView(flow_id, flow.verification_url, flow.expires_at)

    def get_qrcode_path(self, flow_id: str) -> Path | None:
        self._cleanup_expired()
        with self._flow_lock:
            flow = self._flows.get(flow_id)
            if flow is not None and flow.qr_code_path.is_file():
                return flow.qr_code_path
            configuration_flow = self._configuration_flows.get(flow_id)
            if configuration_flow is not None and configuration_flow.qr_code_path.is_file():
                return configuration_flow.qr_code_path
        return None

    def complete_user_authorization(self, flow_id: str) -> LarkCliStatus:
        self._cleanup_expired()
        flow = self._flows.pop(flow_id, None)
        if flow is None:
            raise RuntimeError("This Feishu authorization flow has expired. Start a new one.")
        try:
            self._adapter.complete_user_authorization(device_code=flow.device_code)
            return self._adapter.inspect()
        finally:
            self._remove_qrcode(flow.qr_code_path)

    def _cleanup_expired(self) -> None:
        now = datetime.now(UTC)
        with self._flow_lock:
            expired_ids = [
                flow_id for flow_id, flow in self._flows.items() if flow.expires_at <= now
            ]
            for flow_id in expired_ids:
                flow = self._flows.pop(flow_id)
                self._remove_qrcode(flow.qr_code_path)
            expired_configuration_ids = [
                flow_id
                for flow_id, flow in self._configuration_flows.items()
                if flow.expires_at <= now
            ]
            for flow_id in expired_configuration_ids:
                configuration_flow = self._configuration_flows.pop(flow_id)
                if configuration_flow.process.poll() is None:
                    configuration_flow.process.terminate()
                self._remove_qrcode(configuration_flow.qr_code_path)

    def _monitor_cli_configuration(self, flow_id: str) -> None:
        """Extract the CLI-provided setup URL and keep its QR image inside project data only."""

        with self._flow_lock:
            flow = self._configuration_flows.get(flow_id)
        if flow is None or flow.process.stdout is None:
            return
        try:
            for line in flow.process.stdout:
                verification_url = self._extract_verification_url(line)
                if verification_url is None or flow.verification_url is not None:
                    continue
                flow.qr_code_path.parent.mkdir(parents=True, exist_ok=True)
                self._adapter.render_qrcode(
                    verification_url=verification_url,
                    output_path=flow.qr_code_path,
                    project_root=self._project_root,
                )
                with self._flow_lock:
                    current = self._configuration_flows.get(flow_id)
                    if current is not None:
                        current.verification_url = verification_url
                        current.status = "awaiting_browser"
            return_code = flow.process.wait()
            with self._flow_lock:
                current = self._configuration_flows.get(flow_id)
                if current is not None:
                    current.status = "completed" if return_code == 0 else "failed"
        except (OSError, RuntimeError, subprocess.SubprocessError):
            if flow.process.poll() is None:
                try:
                    flow.process.terminate()
                except OSError:
                    pass
            with self._flow_lock:
                current = self._configuration_flows.get(flow_id)
                if current is not None:
                    current.status = "failed"

    @staticmethod
    def _extract_verification_url(value: str) -> str | None:
        match = re.search(r"https://[^\\s<>\"']+", value)
        return match.group(0).rstrip(".,;:)]}") if match is not None else None

    @staticmethod
    def _remove_qrcode(path: Path) -> None:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
