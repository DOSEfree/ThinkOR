"""Short-lived, non-persistent orchestration for Feishu user authorization."""

from __future__ import annotations

import secrets
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


class LarkSetupService:
    """Keep device codes only in process memory for one short authorization flow."""

    def __init__(self, *, adapter: LarkCliStatusAdapter, project_root: Path) -> None:
        self._adapter = adapter
        self._project_root = project_root
        self._flows: dict[str, _LarkSetupFlow] = {}

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

    def get_flow(self, flow_id: str) -> LarkSetupFlowView | None:
        self._cleanup_expired()
        flow = self._flows.get(flow_id)
        if flow is None:
            return None
        return LarkSetupFlowView(flow_id, flow.verification_url, flow.expires_at)

    def get_qrcode_path(self, flow_id: str) -> Path | None:
        self._cleanup_expired()
        flow = self._flows.get(flow_id)
        return flow.qr_code_path if flow is not None and flow.qr_code_path.is_file() else None

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
        expired_ids = [flow_id for flow_id, flow in self._flows.items() if flow.expires_at <= now]
        for flow_id in expired_ids:
            flow = self._flows.pop(flow_id)
            self._remove_qrcode(flow.qr_code_path)

    @staticmethod
    def _remove_qrcode(path: Path) -> None:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
