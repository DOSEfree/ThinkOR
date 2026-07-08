"""Minimal FastAPI application for the current IdeaOS-Agent slices."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from ideaos_agent.api.follow_up import router as follow_up_router
from ideaos_agent.api.idea_analysis import router as idea_analysis_router
from ideaos_agent.api.session_history import router as session_history_router
from ideaos_agent.config import get_settings
from ideaos_agent.presentation.web import router as presentation_router

STATIC_DIR = Path(__file__).resolve().parent / "presentation" / "static"


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    settings = get_settings()
    app = FastAPI(title=settings.app_name, debug=settings.debug)

    @app.get("/")
    def read_root() -> dict[str, str]:
        return {
            "name": settings.app_name,
            "environment": settings.environment,
            "status": "ready",
        }

    @app.get("/health")
    def healthcheck() -> dict[str, str]:
        return {"status": "ok"}

    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    app.include_router(presentation_router)
    app.include_router(idea_analysis_router)
    app.include_router(follow_up_router)
    app.include_router(session_history_router)

    return app


app = create_app()
