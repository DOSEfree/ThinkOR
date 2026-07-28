"""Local-only Feishu user authorization endpoints with ephemeral flow state."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse

from ideaos_agent.api.dependencies import get_lark_setup_service
from ideaos_agent.api.local_management import (
    require_local_management_access,
    require_local_management_read_access,
)
from ideaos_agent.application.lark_setup_service import LarkSetupService
from ideaos_agent.config import get_settings

router = APIRouter(prefix="/api/v1/lark", tags=["lark-setup"])
LarkSetupServiceDependency = Annotated[LarkSetupService, Depends(get_lark_setup_service)]
LocalAccessDependency = Annotated[None, Depends(require_local_management_access)]
LocalReadAccessDependency = Annotated[None, Depends(require_local_management_read_access)]


@router.post("/setup/start")
def start_lark_setup(
    _: LocalAccessDependency,
    service: LarkSetupServiceDependency,
) -> dict[str, str]:
    """Start one short-lived user QR authorization; no device code leaves memory."""

    if get_settings().feishu_archive_as != "user":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "bot_identity_requires_console_setup",
                "message": (
                    "Bot archive identity must be configured in the Feishu developer console."
                ),
            },
        )
    try:
        flow = service.start_user_authorization()
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "lark_setup_unavailable", "message": str(exc)},
        ) from exc
    return {
        "flow_id": flow.flow_id,
        "verification_url": flow.verification_url,
        "expires_at": flow.expires_at.isoformat(),
    }


@router.get("/setup/{flow_id}/qrcode")
def get_lark_setup_qrcode(
    flow_id: str,
    _: LocalReadAccessDependency,
    service: LarkSetupServiceDependency,
) -> FileResponse:
    """Serve an active, controlled QR PNG only to the originating local page."""

    path = service.get_qrcode_path(flow_id)
    if path is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "lark_setup_expired",
                "message": "The authorization QR code has expired.",
            },
        )
    return FileResponse(path, media_type="image/png", headers={"Cache-Control": "no-store"})


@router.post("/setup/{flow_id}/complete")
def complete_lark_setup(
    flow_id: str,
    _: LocalAccessDependency,
    service: LarkSetupServiceDependency,
) -> dict[str, str]:
    """Complete user authorization then discard all flow-specific ephemeral data."""

    try:
        result = service.complete_user_authorization(flow_id)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "lark_setup_incomplete", "message": str(exc)},
        ) from exc
    return {"availability": result.availability, "next_step": result.next_step}


@router.post("/recheck")
def recheck_lark(
    _: LocalAccessDependency,
    service: LarkSetupServiceDependency,
) -> dict[str, str | None]:
    """Re-run authentication checking without storing CLI output."""

    result = service.recheck()
    return {
        "availability": result.availability,
        "identity": result.identity,
        "version": result.version,
        "next_step": result.next_step,
    }
