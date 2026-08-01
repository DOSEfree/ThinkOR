from pathlib import Path

from ideaos_agent import config
from ideaos_agent.config import resolve_project_root


def test_resolve_project_root_prefers_project_working_directory(tmp_path: Path) -> None:
    project_directory = tmp_path / "ThinkOR"
    project_directory.mkdir()
    (project_directory / "pyproject.toml").write_text("[project]\nname = 'thinkor'\n")

    assert resolve_project_root(project_directory) == project_directory


def test_resolve_project_root_accepts_nested_project_directory(tmp_path: Path) -> None:
    project_directory = tmp_path / "ThinkOR"
    nested_directory = project_directory / "scripts" / "local"
    nested_directory.mkdir(parents=True)
    (project_directory / ".env.example").write_text("IDEAOS_USE_FAKE_LLM=true\n")

    assert resolve_project_root(nested_directory) == project_directory


def test_settings_default_to_dual_fake_without_dotenv(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(config, "ENV_FILE_PATH", tmp_path / ".env")
    monkeypatch.delenv("IDEAOS_USE_FAKE_LLM", raising=False)
    monkeypatch.delenv("IDEAOS_USE_FAKE_ARCHIVE", raising=False)
    monkeypatch.delenv("IDEAOS_FEISHU_ARCHIVE_AS", raising=False)

    settings = config.get_settings()

    assert settings.use_fake_llm is True
    assert settings.use_fake_archive is True
    assert settings.feishu_archive_as == "bot"


def test_explicit_process_environment_overrides_dotenv_modes(
    monkeypatch, tmp_path: Path
) -> None:
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text(
        "IDEAOS_USE_FAKE_LLM=true\nIDEAOS_USE_FAKE_ARCHIVE=true\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(config, "ENV_FILE_PATH", dotenv_path)
    monkeypatch.setenv("IDEAOS_USE_FAKE_LLM", "false")
    monkeypatch.setenv("IDEAOS_USE_FAKE_ARCHIVE", "false")

    settings = config.get_settings()

    assert settings.use_fake_llm is False
    assert settings.use_fake_archive is False
