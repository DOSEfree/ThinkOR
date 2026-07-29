import subprocess

from ideaos_agent.infrastructure.archive.lark_cli_status import LarkCliStatusAdapter


def test_inspect_returns_authenticated_state_from_current_status_shape(monkeypatch) -> None:
    adapter = LarkCliStatusAdapter(command="lark-cli", archive_as="user", timeout_seconds=3)
    monkeypatch.setattr(
        "ideaos_agent.infrastructure.archive.lark_cli_status.shutil.which",
        lambda _command: "C:/tools/lark-cli.exe",
    )
    responses = iter(
        [
            subprocess.CompletedProcess(["lark-cli", "--version"], 0, "1.0.77\n", ""),
            subprocess.CompletedProcess(
                ["lark-cli", "auth", "status"],
                0,
                (
                    '{"identity": "user", "verified": true, "identities": {'
                    '"user": {"status": "ready", "verified": true}, '
                    '"bot": {"status": "ready", "verified": true}}}'
                ),
                "",
            ),
        ]
    )
    monkeypatch.setattr(adapter, "_run", lambda *_args, **_kwargs: next(responses))

    result = adapter.inspect()

    assert result.availability == "authenticated_unverified"
    assert result.identity == "user"
    assert result.version == "1.0.77"
    assert result.next_step == "try_archive"


def test_inspect_returns_unauthenticated_when_selected_identity_is_not_ready(monkeypatch) -> None:
    adapter = LarkCliStatusAdapter(command="lark-cli", archive_as="user", timeout_seconds=3)
    monkeypatch.setattr(
        "ideaos_agent.infrastructure.archive.lark_cli_status.shutil.which",
        lambda _command: "C:/tools/lark-cli.exe",
    )
    responses = iter(
        [
            subprocess.CompletedProcess(["lark-cli", "--version"], 0, "1.0.77\n", ""),
            subprocess.CompletedProcess(
                ["lark-cli", "auth", "status"],
                0,
                (
                    '{"identity": "bot", "verified": false, "identities": {'
                    '"user": {"status": "expired", "verified": false}, '
                    '"bot": {"status": "unavailable", "verified": false}}}'
                ),
                "",
            ),
        ]
    )
    monkeypatch.setattr(adapter, "_run", lambda *_args, **_kwargs: next(responses))

    result = adapter.inspect()

    assert result.availability == "unauthenticated"
    assert result.next_step == "authorize_user"


def test_inspect_detects_ready_other_identity_as_mismatch(monkeypatch) -> None:
    adapter = LarkCliStatusAdapter(command="lark-cli", archive_as="user", timeout_seconds=3)
    monkeypatch.setattr(
        "ideaos_agent.infrastructure.archive.lark_cli_status.shutil.which",
        lambda _command: "C:/tools/lark-cli.exe",
    )
    responses = iter(
        [
            subprocess.CompletedProcess(["lark-cli", "--version"], 0, "1.0.77\n", ""),
            subprocess.CompletedProcess(
                ["lark-cli", "auth", "status"],
                0,
                (
                    '{"identity": "bot", "verified": true, "identities": {'
                    '"user": {"status": "expired", "verified": false}, '
                    '"bot": {"status": "ready", "verified": true}}}'
                ),
                "",
            ),
        ]
    )
    monkeypatch.setattr(adapter, "_run", lambda *_args, **_kwargs: next(responses))

    result = adapter.inspect()

    assert result.availability == "identity_mismatch"
    assert result.identity == "bot"


def test_inspect_returns_unresponsive_when_cli_status_check_times_out(monkeypatch) -> None:
    adapter = LarkCliStatusAdapter(command="lark-cli", archive_as="user", timeout_seconds=3)
    monkeypatch.setattr(
        "ideaos_agent.infrastructure.archive.lark_cli_status.shutil.which",
        lambda _command: "C:/tools/lark-cli.exe",
    )

    def fail_run(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired("lark-cli", 3)

    monkeypatch.setattr(adapter, "_run", fail_run)

    result = adapter.inspect()

    assert result.availability == "cli_unresponsive"
    assert result.next_step == "retry_cli_check"


def test_start_authorization_requires_ephemeral_url_and_device_code(monkeypatch) -> None:
    adapter = LarkCliStatusAdapter(command="lark-cli", archive_as="user", timeout_seconds=3)
    monkeypatch.setattr(
        "ideaos_agent.infrastructure.archive.lark_cli_status.shutil.which",
        lambda _command: "C:/tools/lark-cli.exe",
    )
    monkeypatch.setattr(
        adapter,
        "_run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess(
            ["lark-cli", "auth", "login"],
            0,
            (
                '{"ok": true, "data": {"verification_url": '
                '"https://example.test/auth", "device_code": "one-time"}}'
            ),
            "",
        ),
    )

    result = adapter.start_user_authorization()

    assert result.verification_url == "https://example.test/auth"
    assert result.device_code == "one-time"
