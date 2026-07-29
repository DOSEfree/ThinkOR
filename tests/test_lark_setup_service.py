from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

from ideaos_agent.application.lark_setup_service import LarkSetupService, _LarkConfigurationFlow


def test_cli_configuration_monitor_terminates_process_when_qrcode_rendering_fails(tmp_path) -> None:
    process = Mock()
    process.stdout = iter(["Open https://example.test/verify\n"])
    process.poll.return_value = None
    adapter = Mock()
    adapter.render_qrcode.side_effect = RuntimeError("QR rendering failed")
    service = LarkSetupService(adapter=adapter, project_root=tmp_path)
    flow_id = "configuration-flow"
    service._configuration_flows[flow_id] = _LarkConfigurationFlow(  # noqa: SLF001
        process=process,
        expires_at=datetime.now(UTC) + timedelta(minutes=10),
        qr_code_path=tmp_path / "data" / "lark_setup" / "configuration-flow.png",
    )

    service._monitor_cli_configuration(flow_id)  # noqa: SLF001

    process.terminate.assert_called_once()
    assert service.get_cli_configuration(flow_id).status == "failed"
