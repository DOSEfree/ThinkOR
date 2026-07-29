from pathlib import Path

import pytest
from fastapi import HTTPException

from ideaos_agent.api.runtime_capabilities import apply_local_config
from ideaos_agent.application.local_config_service import LocalConfigService
from ideaos_agent.config import get_settings
from ideaos_agent.domain.runtime import RuntimeModeSelection, RuntimeModeSelectionError
from ideaos_agent.infrastructure.config.dotenv_store import DotenvModeStore, DotenvStoreError
from ideaos_agent.models import RuntimeModeInput


def test_update_creates_dotenv_from_template_and_only_changes_modes(tmp_path: Path) -> None:
    template_path = tmp_path / ".env.example"
    dotenv_path = tmp_path / ".env"
    template_path.write_text(
        "# Keep this comment\n"
        "IDEAOS_USE_FAKE_LLM=true\n"
        "IDEAOS_USE_FAKE_ARCHIVE=true\n"
        "IDEAOS_LLM_API_KEY=\n",
        encoding="utf-8",
    )
    store = DotenvModeStore(dotenv_path=dotenv_path, template_path=template_path)

    result = store.update_modes(
        RuntimeModeSelection(use_fake_llm=False, use_fake_archive=True)
    )

    content = dotenv_path.read_text(encoding="utf-8")
    assert result.created_from_template is True
    assert "# Keep this comment" in content
    assert "IDEAOS_USE_FAKE_LLM=false" in content
    assert "IDEAOS_USE_FAKE_ARCHIVE=true" in content
    assert "IDEAOS_LLM_API_KEY=" in content


def test_update_preserves_existing_secret_and_other_values(tmp_path: Path) -> None:
    template_path = tmp_path / ".env.example"
    dotenv_path = tmp_path / ".env"
    template_path.write_text("IDEAOS_USE_FAKE_LLM=true\n", encoding="utf-8")
    dotenv_path.write_text(
        "# Existing settings\n"
        "IDEAOS_USE_FAKE_LLM=true\n"
        "IDEAOS_USE_FAKE_ARCHIVE=true\n"
        "IDEAOS_LLM_API_KEY=secret-value\n"
        "IDEAOS_LLM_MODEL=existing-model\n",
        encoding="utf-8",
    )
    store = DotenvModeStore(dotenv_path=dotenv_path, template_path=template_path)

    result = store.update_modes(
        RuntimeModeSelection(use_fake_llm=False, use_fake_archive=False)
    )

    content = dotenv_path.read_text(encoding="utf-8")
    assert result.created_from_template is False
    assert "# Existing settings" in content
    assert "IDEAOS_USE_FAKE_LLM=false" in content
    assert "IDEAOS_USE_FAKE_ARCHIVE=false" in content
    assert "IDEAOS_LLM_API_KEY=secret-value" in content
    assert "IDEAOS_LLM_MODEL=existing-model" in content


def test_fake_llm_with_real_archive_requires_acknowledgement(tmp_path: Path) -> None:
    template_path = tmp_path / ".env.example"
    dotenv_path = tmp_path / ".env"
    template_path.write_text("IDEAOS_USE_FAKE_LLM=true\n", encoding="utf-8")
    store = DotenvModeStore(dotenv_path=dotenv_path, template_path=template_path)

    with pytest.raises(RuntimeModeSelectionError):
        store.update_modes(RuntimeModeSelection(use_fake_llm=True, use_fake_archive=False))

    assert not dotenv_path.exists()


def test_failed_write_keeps_existing_dotenv_unchanged(monkeypatch, tmp_path: Path) -> None:
    template_path = tmp_path / ".env.example"
    dotenv_path = tmp_path / ".env"
    template_path.write_text("IDEAOS_USE_FAKE_LLM=true\n", encoding="utf-8")
    original_content = "IDEAOS_USE_FAKE_LLM=true\nIDEAOS_USE_FAKE_ARCHIVE=true\n"
    dotenv_path.write_text(original_content, encoding="utf-8")
    store = DotenvModeStore(dotenv_path=dotenv_path, template_path=template_path)

    def fail_set_key(*_args: object, **_kwargs: object) -> None:
        raise OSError("simulated write failure")

    monkeypatch.setattr(
        "ideaos_agent.infrastructure.config.dotenv_store.set_key",
        fail_set_key,
    )

    with pytest.raises(DotenvStoreError):
        store.update_modes(RuntimeModeSelection(use_fake_llm=False, use_fake_archive=True))

    assert dotenv_path.read_text(encoding="utf-8") == original_content
    assert not list(tmp_path.glob(".thinkor-env-*.tmp"))


def test_local_config_service_reports_process_override(monkeypatch, tmp_path: Path) -> None:
    from ideaos_agent import config

    template_path = tmp_path / ".env.example"
    dotenv_path = tmp_path / ".env"
    template_path.write_text(
        "IDEAOS_USE_FAKE_LLM=true\nIDEAOS_USE_FAKE_ARCHIVE=true\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(config, "ENV_FILE_PATH", dotenv_path)
    monkeypatch.delenv("IDEAOS_USE_FAKE_ARCHIVE", raising=False)
    monkeypatch.setenv("IDEAOS_USE_FAKE_LLM", "true")
    service = LocalConfigService(
        dotenv_store=DotenvModeStore(dotenv_path=dotenv_path, template_path=template_path),
        settings_loader=get_settings,
        process_environment={"IDEAOS_USE_FAKE_LLM": "true"},
    )

    result = service.apply_runtime_modes(
        RuntimeModeSelection(use_fake_llm=False, use_fake_archive=False)
    )

    assert result.effective_use_fake_llm is True
    assert result.effective_use_fake_archive is False
    assert result.process_environment_overrides == ("IDEAOS_USE_FAKE_LLM",)


def test_apply_local_config_returns_json_conflict_when_dotenv_is_unavailable() -> None:
    class UnavailableLocalConfigService:
        def apply_runtime_modes(self, _selection: RuntimeModeSelection) -> None:
            raise DotenvStoreError("template is missing")

    with pytest.raises(HTTPException) as exc_info:
        apply_local_config(
            RuntimeModeInput(use_fake_llm=True, use_fake_archive=True),
            None,
            UnavailableLocalConfigService(),
            None,
        )

    unavailable_message = (
        "无法更新本地运行设置。请从 ThinkOR 项目根目录启动服务，"
        "并确认 .env.example 存在且可读取。"
    )
    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == {
        "code": "local_config_unavailable",
        "message": unavailable_message,
    }
