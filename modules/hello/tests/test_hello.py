"""`hello` offers `hello.greeting` 1.0 and serves one page; its manifest is valid."""

from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from contracts.hello_greeting.v1 import GreetingV1
from modules.hello.manifest import manifest
from rmi_core.manifest import SeamImpl


def test_manifest_offers_the_greeting_seam() -> None:
    (seam,) = manifest.seams_offered
    assert isinstance(seam, SeamImpl)
    assert (seam.name, seam.version) == ("hello.greeting", "1.0")
    impl: GreetingV1 = seam.impl  # type: ignore[assignment]
    assert impl.greet("Ann").message == "Hello, Ann!"


def test_one_nav_item_under_its_own_prefix() -> None:
    (nav,) = manifest.nav
    assert nav.path == "/hello"


def test_page_renders() -> None:
    app = FastAPI()
    for router in manifest.routers:
        app.include_router(router, prefix="/hello")  # type: ignore[arg-type]
    client: Any = TestClient(app)
    response: Any = client.get("/hello/")
    assert response.status_code == 200
    assert "Hello, world!" in response.text
