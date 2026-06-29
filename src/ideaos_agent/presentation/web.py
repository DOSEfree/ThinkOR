"""Presentation routes for the minimal Swiss Style web interface."""

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

router = APIRouter(tags=["presentation"])


@router.get("/app", response_class=HTMLResponse)
def read_app(request: Request) -> HTMLResponse:
    """Render the minimal single-page interface."""

    return templates.TemplateResponse(
        request=request,
        name="app.html",
        context={
            "page_title": "IdeaOS-Agent / App",
            "app_name": "IdeaOS-Agent",
        },
    )
