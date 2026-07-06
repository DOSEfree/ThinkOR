"""HTTP endpoints for v0.2.5 follow-up refinement flows."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from ideaos_agent.api.dependencies import get_follow_up_session_service
from ideaos_agent.application.follow_up_session_service import FollowUpSessionService
from ideaos_agent.domain.errors import (
    IdeaInputTooLongError,
    LlmRequestError,
    LlmResponseFormatError,
    LlmTimeoutError,
    SessionNotFoundError,
    SessionStateError,
)
from ideaos_agent.models import (
    ComposedPlanResponse,
    ComposeFullPlanInput,
    FollowUpInput,
    FollowUpResponse,
)

router = APIRouter(prefix="/api/v1/follow-up", tags=["follow-up"])
FollowUpSessionServiceDependency = Annotated[
    FollowUpSessionService,
    Depends(get_follow_up_session_service),
]


@router.post("/refine", response_model=FollowUpResponse)
def refine_follow_up(
    payload: FollowUpInput,
    service: FollowUpSessionServiceDependency,
) -> FollowUpResponse:
    """Run one bounded follow-up refinement request."""

    try:
        return service.refine(payload)
    except IdeaInputTooLongError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": "idea_input_too_long", "message": str(exc)},
        ) from exc
    except SessionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "session_not_found", "message": str(exc)},
        ) from exc
    except SessionStateError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "session_state_error", "message": str(exc)},
        ) from exc
    except LlmTimeoutError as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail={"code": "llm_timeout", "message": str(exc)},
        ) from exc
    except LlmRequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "llm_request_error", "message": str(exc)},
        ) from exc
    except LlmResponseFormatError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "llm_response_format_error", "message": str(exc)},
        ) from exc


@router.post("/compose-full-plan", response_model=ComposedPlanResponse)
def compose_full_plan(
    payload: ComposeFullPlanInput,
    service: FollowUpSessionServiceDependency,
) -> ComposedPlanResponse:
    """Compose a new full plan from one completed refinement session."""

    try:
        return service.compose_full_plan(payload)
    except SessionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "session_not_found", "message": str(exc)},
        ) from exc
    except SessionStateError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "session_state_error", "message": str(exc)},
        ) from exc
