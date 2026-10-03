"""The one page of `hello_friend`, mounted by the core at `/hello_friend`."""

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse

from contracts.hello_greeting.v1 import GreetingV1
from modules.hello_friend.seams import greeting_provider

router = APIRouter()

Provider = Annotated[GreetingV1 | None, Depends(greeting_provider)]


@router.get("/", response_class=HTMLResponse, name="hello_friend.index")
def index(greeter: Provider) -> str:
    if greeter is None:
        return "<p>Greetings are off: no module offers hello.greeting.</p>"
    return f"<h1>{greeter.greet('friend').message}</h1>"
