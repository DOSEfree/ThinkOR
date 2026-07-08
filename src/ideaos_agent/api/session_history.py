"""HTTP endpoints for v0.3.0 session history and thread queries."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ideaos_agent.api.dependencies import get_session_history_service
from ideaos_agent.application.session_history_service import SessionHistoryService
from ideaos_agent.domain.errors import SessionNotFoundError
from ideaos_agent.models import (
    SessionDetailResponse,
    SessionListResponse,
    SessionThreadResponse,
    ThreadListResponse,
)

router = APIRouter(prefix="/api/v1", tags=["session-history"])
SessionHistoryServiceDependency = Annotated[
    SessionHistoryService,
    Depends(get_session_history_service),
]


@router.get("/sessions", response_model=SessionListResponse)
def list_sessions(
    service: SessionHistoryServiceDependency,
    limit: int = Query(default=20, ge=1, le=200),
) -> SessionListResponse:
    """List recent local sessions for history navigation."""

    return service.list_sessions(limit=limit)


@router.get("/sessions/{session_id}", response_model=SessionDetailResponse)
def get_session_detail(
    session_id: str,
    service: SessionHistoryServiceDependency,
) -> SessionDetailResponse:
    """Fetch one detailed local session view."""

    try:
        return service.get_session_detail(session_id)
    except SessionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "session_not_found", "message": str(exc)},
        ) from exc


@router.get("/threads", response_model=ThreadListResponse)
def list_threads(
    service: SessionHistoryServiceDependency,
    limit: int = Query(default=20, ge=1, le=200),
) -> ThreadListResponse:
    """List recent idea threads grouped by root session."""

    return service.list_threads(limit=limit)


@router.get("/threads/{root_session_id}", response_model=SessionThreadResponse)
def get_thread(
    root_session_id: str,
    service: SessionHistoryServiceDependency,
) -> SessionThreadResponse:
    """Fetch all sessions in one idea thread."""

    try:
        return service.get_thread(root_session_id)
    except SessionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "session_not_found", "message": str(exc)},
        ) from exc
