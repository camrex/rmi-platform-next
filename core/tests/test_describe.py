"""`describe` reports what the loaded modules declare, as JSON (PROPOSAL §5): modules, routes, nav,
link kinds, seams with generated JSON Schemas, permissions, jobs. Module keys here are invented."""

from __future__ import annotations

import json
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any
from unittest.mock import patch

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from rmi_core.describe import (
    DESCRIBE_PATH,
    contract_module_name,
    describe,
    describe_router,
    main,
)
from rmi_core.loader import LoadedModules
from rmi_core.manifest import (
    AccessKey,
    Job,
    LinkKind,
    ModuleManifest,
    Nav,
    Owned,
    Permissions,
    SeamImpl,
    SeamRef,
)
from rmi_core.resolve import resolve


class Greeting(BaseModel):
    who: str
    times: int = 1


class _NotModel:
    """Not pydantic: ignored when generating schemas."""


Greeting.__module__ = "contracts.hello_greeting.v1"
_NotModel.__module__ = "contracts.hello_greeting.v1"


def _contract_module() -> ModuleType:
    mod = ModuleType("contracts.hello_greeting.v1")
    mod.Greeting = Greeting  # type: ignore[attr-defined]
    mod._NotModel = _NotModel  # type: ignore[attr-defined]
    mod.Imported = BaseModel  # type: ignore[attr-defined]  # defined elsewhere: not described
    return mod


def importer(name: str) -> ModuleType:
    if name == "contracts.hello_greeting.v1":
        return _contract_module()
    if name == "contracts.hello_broken.v1":
        raise RuntimeError("boom")
    raise ModuleNotFoundError(f"No module named {name!r}", name="contracts")


def send_greeting() -> None: ...


def pages() -> APIRouter:
    router = APIRouter()

    @router.get("/pages", name="hello_pages")
    def hello_pages() -> str:  # pyright: ignore[reportUnusedFunction]
        return "hi"

    @router.post("/pages")
    def post_pages() -> str:  # pyright: ignore[reportUnusedFunction]
        return "ok"

    return router


def hello() -> ModuleManifest:
    return ModuleManifest(
        key="hello",
        version="1.2",
        display_name="Hello",
        accent="teal",
        routers=[pages()],
        permissions=Permissions(
            facets=["edit:greetings"],
            capabilities=["hello.shout"],
            access_keys=[AccessKey("finance", "Finance")],
        ),
        nav=[Nav("Pages", "/hello/pages", facet="edit:greetings")],
        jobs=[Job(send_greeting, cron="0 6 * * *")],
        links_offered=[
            LinkKind("hello.page", Owned(), "/hello/pages/{id}", "Hello page", "edit:greetings")
        ],
        seams_offered=[SeamImpl("hello.greeting", "1.2", send_greeting)],
    )


def friend(range_: str = ">=1,<2", *, requires: bool = False) -> ModuleManifest:
    ref = [SeamRef("hello.greeting", range_)]
    return ModuleManifest(
        key="friend",
        version="0.1",
        display_name="Friend",
        accent="blue",
        requires=ref if requires else (),
        uses=() if requires else ref,
    )


def load(*manifests: ModuleManifest) -> LoadedModules:
    resolution = resolve(manifests)
    by_key = {m.key: m for m in manifests}
    return LoadedModules(tuple(by_key[k] for k in resolution.load_order), resolution)


def doc(*manifests: ModuleManifest) -> dict[str, Any]:
    return describe(load(*manifests), importer=importer)


def test_empty_platform() -> None:
    result = doc()
    assert result["modules"] == [] and result["seams"] == [] and result["load_order"] == []
    assert result["describe_version"] == 1


def test_decisions_come_from_front_matter(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Index\n")
    (tmp_path / "0000-template.md").write_text("---\nstatus: open\nkind: x\n---\n# <Title>\n")
    (tmp_path / "notes.txt").write_text("not markdown")
    (tmp_path / "0002-b.md").write_text(
        "---\nstatus: open\nkind: ruling\nrefs: []\n---\n# Second\n"
    )
    (tmp_path / "0001-a.md").write_text(
        '---\nstatus: ruled\nkind: architecture\nsource_status: "Accepted"\n---\n'
        "# 0001 \u2014 First one\n\nbody\n"
    )
    (tmp_path / "0003-c.md").write_text("no front matter\n")
    result = describe(load(), importer=importer, decisions_dir=tmp_path)
    assert result["decisions"] == [
        {"id": "0001", "title": "First one", "status": "ruled", "kind": "architecture"},
        {"id": "0002", "title": "Second", "status": "open", "kind": "ruling"},
        {"id": "0003", "title": "0003-c", "status": None, "kind": None},
    ]


def test_absent_decisions_folder_gives_empty_list(tmp_path: Path) -> None:
    result = describe(load(), importer=importer, decisions_dir=tmp_path / "nope")
    assert result["decisions"] == []


def test_default_decisions_folder_is_the_repo_one() -> None:
    ids = [d["id"] for d in doc()["decisions"]]
    assert "0001" in ids and "0000" not in ids


def test_result_is_plain_json() -> None:
    result = doc(hello(), friend())
    assert json.loads(json.dumps(result)) == result


def test_module_entry_has_manifest_fields_and_dotted_callables() -> None:
    (module,) = doc(hello())["modules"]
    assert module["key"] == "hello" and module["version"] == "1.2" and module["accent"] == "teal"
    assert module["jobs"][0]["name"].endswith("send_greeting")
    assert module["seams_offered"][0]["impl_name"].endswith("send_greeting")


def test_routes_are_mounted_under_the_module_key() -> None:
    result = doc(hello())
    assert [(r["path"], r["methods"]) for r in result["routes"]] == [
        ("/hello/pages", ["GET"]),
        ("/hello/pages", ["POST"]),
    ]
    assert result["routes"][0]["module"] == "hello"
    assert result["routes"][0]["name"] == "hello_pages"
    assert result["modules"][0]["routes"] == [
        {k: v for k, v in r.items() if k != "module"} for r in result["routes"]
    ]


def test_nav_link_kinds_permissions_jobs_are_flat_lists_tagged_with_module() -> None:
    result = doc(hello(), friend())
    assert result["nav"] == [
        {
            "module": "hello",
            "label": "Pages",
            "path": "/hello/pages",
            "facet": "edit:greetings",
            "order": 100,
        }
    ]
    (link,) = result["link_kinds"]
    assert link["module"] == "hello" and link["name"] == "hello.page"
    assert link["route"] == "/hello/pages/{id}"
    (job,) = result["jobs"]
    assert job["module"] == "hello" and job["cron"] == "0 6 * * *"
    perms = {p["module"]: p for p in result["permissions"]}
    assert perms["hello"]["facets"] == ["edit:greetings"]
    assert perms["hello"]["capabilities"] == ["hello.shout"]
    assert perms["hello"]["access_keys"] == [{"key": "finance", "label": "Finance"}]
    assert perms["friend"]["facets"] == [] and perms["friend"]["always_on"] is False


def test_seam_has_generated_json_schema_and_consumers() -> None:
    result = doc(hello(), friend())
    (seam,) = result["seams"]
    assert (seam["name"], seam["version"], seam["provider"]) == ("hello.greeting", "1.2", "hello")
    assert seam["contract"] == "contracts.hello_greeting.v1"
    assert list(seam["schemas"]) == ["Greeting"]  # not _NotModel, not the imported BaseModel
    schema = seam["schemas"]["Greeting"]
    assert schema["properties"]["who"]["type"] == "string"
    assert schema["required"] == ["who"]
    assert seam["consumers"] == [
        {"module": "friend", "how": "uses", "range": ">=1,<2", "satisfied": True}
    ]


def test_required_consumer_and_unsatisfied_range_are_visible() -> None:
    result = doc(hello(), friend(">=2", requires=False))
    assert result["seams"][0]["consumers"][0]["satisfied"] is False
    assert [d["module"] for d in result["disabled"]] == ["friend"]
    assert result["disabled"][0]["seam"] == "hello.greeting"
    assert doc(hello(), friend(requires=True))["seams"][0]["consumers"][0]["how"] == "requires"


def test_absent_provider_is_reported_as_disabled_with_reason() -> None:
    result = doc(friend())
    assert result["seams"] == []
    (off,) = result["disabled"]
    assert off["module"] == "friend" and off["reason"]


def test_missing_contract_is_null_not_an_error() -> None:
    manifest = ModuleManifest(
        key="hello",
        version="1.0",
        display_name="H",
        accent="teal",
        seams_offered=[SeamImpl("hello.other", "1.0", send_greeting)],
    )
    (seam,) = doc(manifest)["seams"]
    assert seam["contract"] is None and seam["schemas"] == {} and seam["contract_error"] is None


def test_broken_contract_is_reported_not_raised() -> None:
    manifest = ModuleManifest(
        key="hello",
        version="1.0",
        display_name="H",
        accent="teal",
        seams_offered=[SeamImpl("hello.broken", "1.0", send_greeting)],
    )
    (seam,) = doc(manifest)["seams"]
    assert seam["contract"] == "contracts.hello_broken.v1"
    assert "boom" in seam["contract_error"] and seam["schemas"] == {}


def test_contract_module_name_uses_major_version() -> None:
    impl = SeamImpl("parts.item_estimate", "2.3", send_greeting)
    assert contract_module_name(impl) == "contracts.parts_item_estimate.v2"


def test_served_at_api_v1_describe() -> None:
    app = FastAPI()
    app.include_router(describe_router(load(hello(), friend()), importer=importer))
    client: Any = TestClient(app)
    response: Any = client.get("/api/v1/describe")
    assert DESCRIBE_PATH == "/api/v1/describe"
    assert response.status_code == 200
    assert response.json() == doc(hello(), friend())


def test_cli_prints_json(capsys: pytest.CaptureFixture[str]) -> None:
    loaded = load(hello())
    with patch("rmi_core.describe.load_modules", return_value=loaded):
        assert main(["describe", "--compact"]) == 0
    out = capsys.readouterr().out
    assert json.loads(out)["load_order"] == ["hello"]
    assert "\n" not in out.strip()


def test_cli_reports_load_problems_and_fails(capsys: pytest.CaptureFixture[str]) -> None:
    bad = SimpleNamespace(name="x", load=lambda: 42)

    def fake(*, group: str) -> list[Any]:
        assert group
        return [bad]

    with patch("rmi_core.loader.entry_points", fake):
        assert main(["describe"]) == 1
    assert "entry point 'x'" in capsys.readouterr().err
