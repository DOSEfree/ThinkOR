"""HTTP endpoints for v0.3.0 session history and thread queries."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ideaos_agent.api.dependencies import get_session_history_service
from ideaos_agent.application.session_history_service import SessionHistoryService
from ideaos_agent.domain.errors import SessionNotFoundError, SessionStateError
from ideaos_agent.models import (
    ArchiveRetryResponse,
    ArchiveSyncResponse,
    SessionDetailResponse,
    SessionLeafDeleteResponse,
    SessionListResponse,
    SessionThreadResponse,
    ThreadDeleteResponse,
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


@router.post("/sessions/{session_id}/retry-archive", response_model=ArchiveRetryResponse)
def retry_failed_archive(
    session_id: str,
    service: SessionHistoryServiceDependency,
) -> ArchiveRetryResponse:
    """Retry one completed session whose previous Feishu archive attempt failed."""

    try:
        return service.retry_failed_archive(session_id)
    except SessionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "session_not_found", "message": str(exc)},
        ) from exc
    except SessionStateError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "archive_retry_not_allowed", "message": str(exc)},
        ) from exc


@router.delete("/sessions/{session_id}", response_model=SessionLeafDeleteResponse)
def delete_leaf_session(
    session_id: str,
    service: SessionHistoryServiceDependency,
) -> SessionLeafDeleteResponse:
    """Delete one non-root formal leaf session and its attached local drafts."""

    try:
        return service.delete_leaf_session(session_id)
    except SessionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "session_not_found", "message": str(exc)},
        ) from exc
    except SessionStateError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "session_state_invalid", "message": str(exc)},
        ) from exc


@router.get("/threads", response_model=ThreadListResponse)
def list_threads(
    service: SessionHistoryServiceDependency,
    limit: int = Query(default=20, ge=1, le=200),
    q: str | None = Query(default=None, max_length=200),
) -> ThreadListResponse:
    """List recent idea threads grouped by root session."""

    return service.list_threads(limit=limit, query=q)


@router.post("/threads/sync-remote-archives", response_model=ArchiveSyncResponse)
def sync_remote_archives(
    service: SessionHistoryServiceDependency,
) -> ArchiveSyncResponse:
    """Sync local history by removing sessions whose remote archives are now missing."""

    return service.sync_remote_archive_deletions()


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


@router.delete("/threads/{root_session_id}", response_model=ThreadDeleteResponse)
def delete_thread(
    root_session_id: str,
    service: SessionHistoryServiceDependency,
) -> ThreadDeleteResponse:
    """Delete one local thread and best-effort delete its linked Feishu archives."""

    try:
        return service.delete_thread(root_session_id)
    except SessionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "session_not_found", "message": str(exc)},
        ) from exc
