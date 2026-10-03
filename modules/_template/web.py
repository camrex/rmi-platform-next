"""The one page of `{{MODULE_KEY}}`, mounted by the core at `/{{MODULE_KEY}}`."""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.get("/", response_class=HTMLResponse, name="{{MODULE_KEY}}.index")
def index() -> str:
    return "<h1>{{MODULE_NAME}}</h1>"
