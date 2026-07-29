"""Presentation routes for the minimal Swiss Style web interface."""

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from ideaos_agent.api.local_management import get_csrf_token
from ideaos_agent.config import get_settings

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

router = APIRouter(tags=["presentation"])


@router.get("/app", response_class=HTMLResponse)
def read_app(request: Request) -> HTMLResponse:
    """Render the minimal single-page interface."""

    settings = get_settings()
    return templates.TemplateResponse(
        request=request,
        name="app.html",
        context={
            "page_title": f"{settings.app_name} / App",
            "app_name": settings.app_name,
            "csrf_token": get_csrf_token(),
        },
    )
