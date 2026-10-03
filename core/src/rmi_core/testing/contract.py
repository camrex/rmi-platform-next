"""The contract test every module runs (PROPOSAL §3.3 step 6, docs/CONTRACT.md).

A module's `tests/test_contract.py` is two lines::

    from rmi_core.testing.contract import assert_contract
    def test_contract() -> None: assert_contract(manifest)

For each way the module's optional `uses` seams can be present or absent (all present, each one
absent on its own, none present) this builds a small app from the manifests that would be loaded
and checks, per scenario:

1. the set resolves, the module is in the load order, and exactly the absent `uses` are reported
   as disabled;
2. every page of the module (GET routes without path parameters, and every nav path) answers
   without a 5xx (an exception in a handler counts as 500), and nav paths answer below 400;
3. no link in a rendered page, and no nav or link kind in `describe`, points at a module that is
   not loaded;
4. `GET /api/v1/describe` answers, lists the module, and lists its nav.

Providers are the other installed modules (the `rmi.modules` entry points); pass `candidates` to
use a fixed set instead. A provider brings the modules it `requires` with it. The core has no seam
registry yet, so the test app puts `{seam name: implementation}` on `app.state.seams`; a module
that wants its provider reads it from there.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from importlib.metadata import entry_points
from typing import Any, cast

from fastapi import FastAPI
from fastapi.testclient import TestClient

from rmi_core.describe import DESCRIBE_PATH, describe, describe_router
from rmi_core.loader import ENTRY_POINT_GROUP, LoadedModules
from rmi_core.manifest import _RESERVED_KEYS, ModuleManifest  # pyright: ignore[reportPrivateUsage]
from rmi_core.resolve import ResolutionError, resolve

__all__ = [
    "Scenario",
    "assert_contract",
    "build_app",
    "contract_problems",
    "installed_manifests",
    "scenarios",
]

_LINK_ATTRS = re.compile(
    r"""\b(?:href|src|action|hx-get|hx-post|hx-put|hx-delete)=["']([^"']*)["']"""
)


@dataclass(frozen=True)
class Scenario:
    """One app to build: the manifests present, and the `uses` seams that are absent."""

    label: str
    manifests: tuple[ModuleManifest, ...]
    absent: tuple[str, ...]


def installed_manifests() -> list[ModuleManifest]:
    """Manifests of every installed module. One that fails to load is skipped (`rmi describe`
    reports it); this helper tests one module, not the others."""
    found: list[ModuleManifest] = []
    for ep in entry_points(group=ENTRY_POINT_GROUP):
        try:
            loaded: object = ep.load()
        except Exception:
            continue
        if isinstance(loaded, ModuleManifest):
            found.append(loaded)
    return found


def _with_requires(keys: Sequence[str], by_key: dict[str, ModuleManifest]) -> set[str]:
    """`keys` plus, transitively, the providers of every seam they `require`."""
    offered = {i.name: m.key for m in by_key.values() for i in m.seams_offered}
    todo, seen = list(keys), set[str]()
    while todo:
        key = todo.pop()
        if key in seen:
            continue
        seen.add(key)
        todo += [offered[r.name] for r in by_key[key].requires if r.name in offered]
    return seen


def scenarios(
    manifest: ModuleManifest, candidates: Sequence[ModuleManifest] | None = None
) -> list[Scenario]:
    """All present, each `uses` absent alone, none present (deduplicated, in that order)."""
    pool = installed_manifests() if candidates is None else list(candidates)
    by_key = {m.key: m for m in pool if m.key != manifest.key}
    by_key[manifest.key] = manifest
    provider: dict[str, str] = {}  # used seam -> key of the module offering an accepted version
    for ref in manifest.uses:
        for key in sorted(by_key):
            offered = by_key[key].seams_offered
            if any(i.name == ref.name and ref.accepts(i.version) for i in offered):
                provider[ref.name] = key
                break
    used = [r.name for r in manifest.uses]
    present_sets = [tuple(n for n in used if n in provider)]
    present_sets += [tuple(n for n in used if n in provider and n != gone) for gone in used]
    present_sets.append(())
    out: list[Scenario] = []
    seen: set[tuple[str, ...]] = set()
    for present in present_sets:
        if present in seen:
            continue
        seen.add(present)
        keys = _with_requires([manifest.key, *(provider[n] for n in present)], by_key)
        absent = tuple(n for n in used if n not in present)
        label = "no `uses` absent" if not absent else "absent: " + ", ".join(absent)
        if not used:
            label = "no `uses`"
        manifests = tuple(by_key[k] for k in sorted(keys))
        out.append(Scenario(label, manifests, absent))
    return out


def build_app(loaded: LoadedModules) -> FastAPI:
    """The test app: each module's routers under `/<key>`, plus `describe` and `app.state.seams`."""
    app = FastAPI()
    for m in loaded.manifests:
        for router in m.routers:
            app.include_router(router, prefix=f"/{m.key}")  # type: ignore[arg-type]
    app.include_router(describe_router(loaded))
    app.state.seams = {i.name: i.impl for m in loaded.manifests for i in m.seams_offered}
    return app


def _known_prefixes(keys: Sequence[str]) -> set[str]:
    return {*keys, *_RESERVED_KEYS}


def _bad_target(path: str, keys: Sequence[str]) -> bool:
    """True for an internal path whose first segment is neither a loaded module nor core's."""
    segment = path.split("?")[0].split("#")[0].strip("/").split("/")[0]
    return segment != "" and segment not in _known_prefixes(keys)


def _scenario_problems(manifest: ModuleManifest, scenario: Scenario) -> list[str]:
    try:
        resolution = resolve(scenario.manifests)
    except ResolutionError as exc:
        return [f"does not resolve: {problem}" for problem in exc.problems]
    problems: list[str] = []
    if manifest.key not in resolution.load_order:
        return [f"{manifest.key!r} is not in the load order {list(resolution.load_order)}"]
    off = tuple(sorted(d.seam for d in resolution.disabled if d.module == manifest.key))
    if off != tuple(sorted(scenario.absent)):
        problems.append(f"disabled features are {list(off)}, expected {sorted(scenario.absent)}")
    by_key = {m.key: m for m in scenario.manifests}
    loaded = LoadedModules(tuple(by_key[k] for k in resolution.load_order), resolution)
    keys = loaded.keys
    document = describe(loaded)

    for row in document["nav"] + document["link_kinds"]:
        path = row.get("path") or row.get("route")
        if _bad_target(str(path), keys):
            who = row["module"]
            problems.append(f"{who}: nav or link kind {path!r} points at an absent module")

    client: Any = TestClient(build_app(loaded), raise_server_exceptions=False)
    mine = [r for r in document["routes"] if r["module"] == manifest.key]
    pages = {r["path"] for r in mine if "GET" in r["methods"] and "{" not in r["path"]}
    navs = {n.path for n in manifest.nav if "{" not in n.path}
    for path in sorted(pages | navs):
        response: Any = client.get(path, follow_redirects=True)
        if response.status_code >= 500:
            problems.append(f"GET {path} answered {response.status_code}")
        elif path in navs and response.status_code >= 400:
            problems.append(f"nav path {path} answered {response.status_code}")
        else:
            for target in _LINK_ATTRS.findall(response.text):
                internal = target.startswith("/") and not target.startswith("//")
                if internal and _bad_target(target, keys):
                    problems.append(f"GET {path} links to {target!r}, which is not a loaded module")

    response = client.get(DESCRIBE_PATH)
    if response.status_code != 200:
        problems.append(f"GET {DESCRIBE_PATH} answered {response.status_code}")
    else:
        body = cast("dict[str, Any]", response.json())
        if manifest.key not in body["load_order"]:
            problems.append("describe does not list the module in load_order")
        if manifest.key not in [m["key"] for m in body["modules"]]:
            problems.append("describe does not list the module in modules")
        listed = {n["path"] for n in body["nav"] if n["module"] == manifest.key}
        if listed != {n.path for n in manifest.nav}:
            problems.append("describe does not list the module's nav")
    return problems


def contract_problems(
    manifest: ModuleManifest, candidates: Sequence[ModuleManifest] | None = None
) -> list[str]:
    """Every contract problem found, one line each, prefixed with the scenario; empty when fine."""
    return [
        f"[{manifest.key}; {s.label}] {p}"
        for s in scenarios(manifest, candidates)
        for p in _scenario_problems(manifest, s)
    ]


def assert_contract(
    manifest: ModuleManifest, candidates: Sequence[ModuleManifest] | None = None
) -> None:
    """Fail with every problem listed. The one call a module's `test_contract.py` makes."""
    problems = contract_problems(manifest, candidates)
    assert not problems, "contract broken:\n" + "\n".join(problems)
