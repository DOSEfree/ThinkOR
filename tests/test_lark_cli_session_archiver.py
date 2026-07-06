import json
import subprocess
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

import pytest

from ideaos_agent.domain.analysis import IdeaAnalysis
from ideaos_agent.domain.archive import ArchiveStatus, SessionArchivePayload
from ideaos_agent.domain.session import SessionKind
from ideaos_agent.infrastructure.archive.lark_cli_archiver import LarkCliSessionArchiver


def build_payload() -> SessionArchivePayload:
    return SessionArchivePayload(
        session_id="sess_archive",
        parent_session_id=None,
        parent_archive_url=None,
        session_kind=SessionKind.ANALYSIS,
        archive_title="独立开发者产品验证工具",
        original_content="我想做一个帮助独立开发者验证产品想法的工具。",
        input_echo="我想做一个帮助独立开发者验证产品想法的工具。",
        clarifications=[],
        assumptions=["假设它以 Web 形式提供。"],
        open_questions=["是否需要在首版支持报告分享？"],
        follow_up_question=None,
        analysis=IdeaAnalysis(
            summary="这是一个帮助独立开发者验证产品想法的 Web 工具。",
            feasibility="技术可行。",
            market="目标用户较明确。",
            knowledge_gaps=["产品验证方法"],
            resource_gaps=["种子用户"],
            team_requirements=["产品负责人"],
            similar_projects=["创业想法分析工具"],
            mvp_roadmap=["定义最小输入输出"],
            long_term_roadmap=["迭代交互体验"],
        ),
        refinement_result=None,
        created_at=datetime(2026, 7, 5, 10, 0, tzinfo=UTC),
        completed_at=datetime(2026, 7, 5, 10, 5, tzinfo=UTC),
    )


def test_lark_cli_archiver_returns_success_and_passes_parent_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    resolved_command = r"C:\Users\Lenovo\AppData\Roaming\npm\lark-cli.cmd"

    monkeypatch.setattr(
        "ideaos_agent.infrastructure.archive.lark_cli_archiver.shutil.which",
        lambda command: resolved_command if command == "lark-cli" else None,
    )

    def fake_run(
        args: Sequence[str],
        **kwargs: Any,
    ) -> subprocess.CompletedProcess[str]:
        captured["command"] = list(args)
        captured["input"] = kwargs["input"]
        captured["encoding"] = kwargs["encoding"]
        return subprocess.CompletedProcess(
            args=list(args),
            returncode=0,
            stdout=json.dumps(
                {
                    "ok": True,
                    "data": {
                        "document": {
                            "document_id": "docx_token",
                            "url": "https://feishu.cn/docx/docx_token",
                        }
                    },
                },
                ensure_ascii=False,
            ),
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    archiver = LarkCliSessionArchiver(
        command="lark-cli",
        archive_as="user",
        parent_token="wiki_token",
        timeout_seconds=10.0,
    )

    result = archiver.archive_session(build_payload())

    assert result.archive_status == ArchiveStatus.SUCCEEDED
    assert result.archive_url == "https://feishu.cn/docx/docx_token"
    assert captured["command"] == [
        resolved_command,
        "docs",
        "+create",
        "--as",
        "user",
        "--json",
        "--content",
        "-",
        "--parent-token",
        "wiki_token",
    ]
    assert captured["encoding"] == "utf-8"
    assert "IdeaOS Archive | 独立开发者产品验证工具" in str(captured["input"])


def test_lark_cli_archiver_returns_failed_result_on_cli_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(
        args: Sequence[str],
        **kwargs: Any,
    ) -> subprocess.CompletedProcess[str]:
        del kwargs
        return subprocess.CompletedProcess(
            args=list(args),
            returncode=1,
            stdout="",
            stderr=json.dumps(
                {
                    "ok": False,
                    "error": {
                        "message": "permission denied",
                    },
                },
                ensure_ascii=False,
            ),
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    archiver = LarkCliSessionArchiver(command="lark-cli")

    result = archiver.archive_session(build_payload())

    assert result.archive_status == ArchiveStatus.FAILED
    assert result.archive_url is None
    assert result.archive_error == "permission denied"
