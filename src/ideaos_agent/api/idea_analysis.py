"""HTTP endpoints for idea analysis."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from ideaos_agent.api.dependencies import get_idea_analysis_session_service
from ideaos_agent.application.idea_analysis_session_service import IdeaAnalysisSessionService
from ideaos_agent.domain.errors import (
    IdeaInputTooLongError,
    LlmNotConfiguredError,
    LlmRequestError,
    LlmResponseFormatError,
    LlmTimeoutError,
)
from ideaos_agent.models import IdeaAnalysisResponse, IdeaInput

router = APIRouter(prefix="/api/v1", tags=["idea-analysis"])
IdeaAnalysisSessionServiceDependency = Annotated[
    IdeaAnalysisSessionService,
    Depends(get_idea_analysis_session_service),
]


@router.post("/idea-analysis", response_model=IdeaAnalysisResponse)
def create_idea_analysis(
    payload: IdeaInput,
    service: IdeaAnalysisSessionServiceDependency,
) -> IdeaAnalysisResponse:
    """Generate an idea analysis response with session and archive metadata."""

    try:
        return service.analyze(payload)
    except IdeaInputTooLongError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "idea_input_too_long",
                "message": str(exc),
            },
        ) from exc
    except LlmNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "llm_not_configured",
                "message": str(exc),
            },
        ) from exc
    except LlmTimeoutError as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail={
                "code": "llm_timeout",
                "message": str(exc),
            },
        ) from exc
    except LlmRequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "code": "llm_request_error",
                "message": str(exc),
            },
        ) from exc
    except LlmResponseFormatError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "code": "llm_response_format_error",
                "message": str(exc),
            },
        ) from exc
