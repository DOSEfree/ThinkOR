"""Local-only runtime mode and Feishu readiness endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from ideaos_agent.api.dependencies import (
    get_local_config_service,
    get_runtime_capability_service,
)
from ideaos_agent.api.local_management import require_local_management_access
from ideaos_agent.application.local_config_service import LocalConfigService
from ideaos_agent.application.runtime_capability_service import (
    RuntimeCapabilities,
    RuntimeCapabilityService,
)
from ideaos_agent.domain.runtime import RuntimeModeSelection, RuntimeModeSelectionError
from ideaos_agent.infrastructure.config.dotenv_store import DotenvStoreError
from ideaos_agent.models import (
    LarkCapabilityResponse,
    LocalConfigApplyResponse,
    RuntimeCapabilitiesResponse,
    RuntimeModeInput,
)

router = APIRouter(prefix="/api/v1", tags=["runtime-capabilities"])
CapabilityServiceDependency = Annotated[
    RuntimeCapabilityService,
    Depends(get_runtime_capability_service),
]
LocalConfigServiceDependency = Annotated[LocalConfigService, Depends(get_local_config_service)]
LocalAccessDependency = Annotated[None, Depends(require_local_management_access)]


@router.get("/runtime-capabilities", response_model=RuntimeCapabilitiesResponse)
def get_runtime_capabilities(service: CapabilityServiceDependency) -> RuntimeCapabilitiesResponse:
    """Return current effective modes and non-secret readiness."""

    return _capabilities_response(service.get_capabilities())


@router.post("/local-config/preview")
def preview_local_config(payload: RuntimeModeInput, _: LocalAccessDependency) -> dict[str, object]:
    """Validate mode choices without changing a file or returning configuration values."""

    selection = _selection(payload)
    try:
        selection.validate()
    except RuntimeModeSelectionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": "acknowledgement_required", "message": str(exc)},
        ) from exc
    return {
        "updated_keys": ["IDEAOS_USE_FAKE_LLM", "IDEAOS_USE_FAKE_ARCHIVE"],
        "requires_acknowledgement": selection.use_fake_llm and not selection.use_fake_archive,
    }


@router.post("/local-config/apply", response_model=LocalConfigApplyResponse)
def apply_local_config(
    payload: RuntimeModeInput,
    _: LocalAccessDependency,
    service: LocalConfigServiceDependency,
) -> LocalConfigApplyResponse:
    """Atomically update only local mode flags and return the effective next-request state."""

    try:
        result = service.apply_runtime_modes(_selection(payload))
    except RuntimeModeSelectionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": "acknowledgement_required", "message": str(exc)},
        ) from exc
    except DotenvStoreError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "local_config_unavailable",
                "message": (
                    "无法更新本地运行设置。请从 ThinkOR 项目根目录启动服务，"
                    "并确认 .env.example 存在且可读取。"
                ),
            },
        ) from exc
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

    try:
        capabilities = _capabilities_response(get_runtime_capability_service().get_capabilities())
    except (OSError, RuntimeError, ValueError):
        capabilities = RuntimeCapabilitiesResponse(
            use_fake_llm=result.effective_use_fake_llm,
            use_fake_archive=result.effective_use_fake_archive,
            llm_state="unknown",
            llm_missing_items=[],
            archive_state="unknown",
            lark=None,
            capabilities_checked=False,
        )

    return LocalConfigApplyResponse(
        **capabilities.model_dump(exclude={"process_environment_overrides"}),
        created_from_template=result.created_from_template,
        updated_keys=["IDEAOS_USE_FAKE_LLM", "IDEAOS_USE_FAKE_ARCHIVE"],
        process_environment_overrides=list(result.process_environment_overrides),
    )


def _selection(payload: RuntimeModeInput) -> RuntimeModeSelection:
    return RuntimeModeSelection(
        use_fake_llm=payload.use_fake_llm,
        use_fake_archive=payload.use_fake_archive,
        acknowledge_fake_llm_real_archive=payload.acknowledge_fake_llm_real_archive,
    )


def _capabilities_response(capabilities: RuntimeCapabilities) -> RuntimeCapabilitiesResponse:
    lark = capabilities.lark
    return RuntimeCapabilitiesResponse(
        use_fake_llm=capabilities.use_fake_llm,
        use_fake_archive=capabilities.use_fake_archive,
        llm_state=capabilities.llm_state,
        llm_missing_items=list(capabilities.llm_missing_items),
        archive_state=capabilities.archive_state,
        lark=(
            LarkCapabilityResponse(
                availability=lark.availability,
                identity=lark.identity,
                version=lark.version,
                next_step=lark.next_step,
                update_available=lark.update_available,
            )
            if lark is not None
            else None
        ),
    )
