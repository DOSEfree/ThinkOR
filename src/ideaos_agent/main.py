"""Minimal FastAPI application for Phase 0 initialization."""

from fastapi import FastAPI

from ideaos_agent.api.idea_analysis import router as idea_analysis_router
from ideaos_agent.config import get_settings


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

    app.include_router(idea_analysis_router)

    return app


app = create_app()
