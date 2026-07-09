from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolate_archive_db(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Keep pytest isolated from real local storage and remote integrations."""

    monkeypatch.setenv("IDEAOS_ARCHIVE_DB_PATH", str(tmp_path / "ideaos_agent_test.db"))
    monkeypatch.setenv("IDEAOS_USE_FAKE_LLM", "true")
    monkeypatch.setenv("IDEAOS_USE_FAKE_ARCHIVE", "true")
