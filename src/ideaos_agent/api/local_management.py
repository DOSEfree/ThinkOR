"""Loopback and same-origin gate for local configuration endpoints."""

from __future__ import annotations

import secrets
from urllib.parse import urlparse

from fastapi import HTTPException, Request, status

from ideaos_agent.config import get_settings

_CSRF_TOKEN = secrets.token_urlsafe(32)
_LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost", "testclient"}


def get_csrf_token() -> str:
    """Return the process-local token embedded in the same-origin app page."""

    return _CSRF_TOKEN


def require_local_management_access(request: Request) -> None:
    """Reject remote, proxied, cross-origin, or non-development write requests."""

    _require_local_request(request)
    origin = request.headers.get("origin")
    host = request.headers.get("host", "")
    if origin is None or not host:
        _forbidden("A same-origin browser request is required.")
    parsed_origin = urlparse(origin)
    if parsed_origin.scheme not in {"http", "https"} or parsed_origin.netloc != host:
        _forbidden("The local configuration request has an invalid origin.")
    if not secrets.compare_digest(request.headers.get("x-thinkor-csrf-token", ""), _CSRF_TOKEN):
        _forbidden("The local configuration page has expired. Reload and try again.")


def require_local_management_read_access(request: Request) -> None:
    """Protect local transient resources when a browser omits Origin on a GET fetch."""

    _require_local_request(request)
    if not secrets.compare_digest(request.headers.get("x-thinkor-csrf-token", ""), _CSRF_TOKEN):
        _forbidden("The local configuration page has expired. Reload and try again.")


def _require_local_request(request: Request) -> None:
    try:
        settings = get_settings()
    except (OSError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "local_config_invalid",
                "message": (
                    "无法应用本地运行设置。请检查 .env 中的数值配置是否有效，"
                    "并确认 ThinkOR 项目目录可读写。"
                ),
            },
        ) from exc
    client_host = request.client.host if request.client is not None else ""
    if settings.environment != "development" or client_host not in _LOOPBACK_HOSTS:
        _forbidden("Local configuration is available only from development loopback.")
    if request.headers.get("x-forwarded-for") or request.headers.get("forwarded"):
        _forbidden("Local configuration is unavailable through a forwarded request.")


def _forbidden(message: str) -> None:
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={"code": "local_access_denied", "message": message},
    )
