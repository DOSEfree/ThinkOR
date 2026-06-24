"""HTTP endpoints for idea analysis."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from ideaos_agent.api.dependencies import get_idea_analysis_service
from ideaos_agent.application.idea_analysis_service import IdeaAnalysisService
from ideaos_agent.domain.errors import (
    IdeaInputTooLongError,
    LlmNotConfiguredError,
    LlmRequestError,
    LlmResponseFormatError,
    LlmTimeoutError,
)
from ideaos_agent.models import IdeaAnalysis, IdeaInput

router = APIRouter(prefix="/api/v1", tags=["idea-analysis"])
IdeaAnalysisServiceDependency = Annotated[
    IdeaAnalysisService,
    Depends(get_idea_analysis_service),
]


@router.post("/idea-analysis", response_model=IdeaAnalysis)
def create_idea_analysis(
    payload: IdeaInput,
    service: IdeaAnalysisServiceDependency,
) -> IdeaAnalysis:
    """Generate a full IdeaAnalysis with a single LLM call."""

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
