"""`hello_friend` uses `hello.greeting`: the page works with the provider and without it."""

from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from contracts.hello_greeting.v1 import GreetingV1
from modules.hello.seams import Greeter
from modules.hello_friend.manifest import manifest
from modules.hello_friend.seams import greeting_provider


def client(provider: GreetingV1 | None) -> Any:
    app = FastAPI()
    for router in manifest.routers:
        app.include_router(router, prefix="/hello_friend")  # type: ignore[arg-type]
    app.dependency_overrides[greeting_provider] = lambda: provider
    result: Any = TestClient(app)
    return result


def test_declares_use_not_requirement() -> None:
    assert [(s.name, s.range) for s in manifest.uses] == [("hello.greeting", ">=1,<2")]
    assert manifest.requires == ()


def test_with_provider() -> None:
    response: Any = client(Greeter()).get("/hello_friend/")
    assert response.status_code == 200
    assert "Hello, friend!" in response.text


def test_without_provider_page_says_feature_is_off() -> None:
    response: Any = client(None).get("/hello_friend/")
    assert response.status_code == 200
    assert "Greetings are off" in response.text
