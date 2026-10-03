"""The page renders."""

from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from modules.{{MODULE_KEY}}.manifest import manifest


def test_page_renders() -> None:
    app = FastAPI()
    for router in manifest.routers:
        app.include_router(router, prefix="/{{MODULE_KEY}}")  # type: ignore[arg-type]
    client: Any = TestClient(app)
    response: Any = client.get("/{{MODULE_KEY}}/")
    assert response.status_code == 200
