"""The contract helper passes a good module and catches a 500, a dead link and a dead nav."""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from rmi_core.manifest import ModuleManifest, Nav, SeamImpl, SeamRef
from rmi_core.testing.contract import contract_problems, scenarios


def make(key: str, router: APIRouter, **extra: object) -> ModuleManifest:
    return ModuleManifest(
        key=key,
        version="0.1.0",
        display_name=key.title(),
        accent="blue",
        routers=[router],
        nav=[Nav("Home", f"/{key}")],
        **extra,  # type: ignore[arg-type]
    )


def page(html: str = "<p>ok</p>") -> APIRouter:
    router = APIRouter()

    @router.get("/", response_class=HTMLResponse)
    def index() -> str:  # pyright: ignore[reportUnusedFunction]
        return html

    return router


def provider() -> ModuleManifest:
    return make("prov", page(), seams_offered=[SeamImpl("prov.thing", "1.0", object())])


def test_scenarios_cover_present_and_absent() -> None:
    m = make("user", page(), uses=[SeamRef("prov.thing", ">=1,<2")])
    found = scenarios(m, [provider()])
    assert [s.absent for s in found] == [(), ("prov.thing",)]
    assert [sorted(x.key for x in s.manifests) for s in found] == [["prov", "user"], ["user"]]


def test_good_module_has_no_problems() -> None:
    m = make("user", page(), uses=[SeamRef("prov.thing", ">=1,<2")])
    assert contract_problems(m, [provider()]) == []


def test_a_500_is_reported_in_every_scenario() -> None:
    router = APIRouter()

    @router.get("/")
    def boom() -> str:  # pyright: ignore[reportUnusedFunction]
        raise RuntimeError("boom")

    problems = contract_problems(make("user", router), [])
    assert any("GET /user answered 500" in p for p in problems)


def test_link_to_absent_module_is_reported() -> None:
    m = make("user", page('<a href="/gone/x">x</a><a href="/user/y">y</a>'))
    problems = contract_problems(m, [])
    assert len(problems) == 1
    assert "'/gone/x'" in problems[0]


def test_unsatisfied_requires_is_reported() -> None:
    m = make("user", page(), requires=[SeamRef("prov.thing", ">=1,<2")])
    problems = contract_problems(m, [])
    assert problems
    assert "does not resolve" in problems[0]
