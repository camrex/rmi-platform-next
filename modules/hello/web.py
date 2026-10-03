"""The one page of `hello`, mounted by the core at `/hello`."""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from modules.hello.seams import Greeter

router = APIRouter()


@router.get("/", response_class=HTMLResponse, name="hello.index")
def index() -> str:
    return f"<h1>{Greeter().greet('world').message}</h1>"
