"""`load_modules()` finds manifests through the `rmi.modules` entry point and resolves them."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import pytest

from rmi_core.loader import ENTRY_POINT_GROUP, load_modules
from rmi_core.manifest import ModuleManifest, SeamImpl, SeamRef
from rmi_core.resolve import ResolutionError


def manifest(key: str, **kw: Any) -> ModuleManifest:
    return ModuleManifest(key=key, version="1.0", display_name=key.title(), accent="teal", **kw)


def ep(name: str, target: object = None, *, error: Exception | None = None) -> Any:
    def load() -> object:
        if error is not None:
            raise error
        return target

    return SimpleNamespace(name=name, load=load)


def discover(*eps: Any) -> Any:
    """Patch discovery; also records the group asked for."""

    def fake(*, group: str) -> list[Any]:
        assert group == ENTRY_POINT_GROUP == "rmi.modules"
        return list(eps)

    return patch("rmi_core.loader.entry_points", fake)


def test_empty_set_loads() -> None:
    with discover():
        loaded = load_modules()
    assert loaded.keys == () and loaded.manifests == () and loaded.disabled == ()


def test_loads_in_load_order_providers_first() -> None:
    parts = manifest("parts", seams_offered=[SeamImpl("parts.items", "1.0", object())])
    shed = manifest("shed", requires=[SeamRef(name="parts.items", range=">=1,<2")])
    with discover(ep("shed", shed), ep("parts", parts)):
        loaded = load_modules()
    assert loaded.keys == ("parts", "shed")
    assert loaded.manifests == (parts, shed)
    assert loaded.get("shed") is shed
    assert loaded.get("nope") is None


def test_absent_uses_is_reported_not_fatal() -> None:
    friend = manifest("friend", uses=[SeamRef(name="hello.greeting", range=">=1,<2")])
    with discover(ep("friend", friend)):
        loaded = load_modules()
    assert loaded.keys == ("friend",)
    assert [(d.module, d.seam) for d in loaded.disabled] == [("friend", "hello.greeting")]


def test_unsatisfied_requires_fails_naming_module_and_range() -> None:
    shed = manifest("shed", requires=[SeamRef(name="parts.items", range=">=1,<2")])
    with (
        discover(ep("shed", shed)),
        pytest.raises(ResolutionError, match=r"module 'shed' requires seam 'parts.items'"),
    ):
        load_modules()


def test_not_a_manifest_names_the_entry_point() -> None:
    with (
        discover(ep("bad", "not a manifest")),
        pytest.raises(ResolutionError, match="entry point 'bad' did not return a ModuleManifest"),
    ):
        load_modules()


def test_import_failure_names_the_entry_point() -> None:
    with (
        discover(ep("broken", error=ImportError("no module x"))),
        pytest.raises(ResolutionError, match="entry point 'broken' failed to load"),
    ):
        load_modules()


def test_entry_point_name_must_equal_manifest_key() -> None:
    with (
        discover(ep("alias", manifest("real"))),
        pytest.raises(
            ResolutionError, match="entry point 'alias' returned a manifest with key 'real'"
        ),
    ):
        load_modules()


def test_every_load_problem_is_reported_together() -> None:
    with (
        discover(ep("a", 1), ep("b", error=RuntimeError("boom"))),
        pytest.raises(ResolutionError) as info,
    ):
        load_modules()
    assert len(info.value.problems) == 2


def test_duplicate_keys_rejected() -> None:
    with (
        discover(ep("a", manifest("a")), ep("a", manifest("a"))),
        pytest.raises(ResolutionError, match="duplicate"),
    ):
        load_modules()


def test_core_revision_is_passed_to_resolve() -> None:
    m = manifest("rev", db_schema="rev", migrations="rev/migrations", core_revision=">=2")
    with discover(ep("rev", m)), pytest.raises(ResolutionError, match="core revision"):
        load_modules(core_revision="1")
        assert load_modules(core_revision="2").keys == ("rev",)


def test_real_discovery_with_nothing_installed() -> None:
    """No patching: the real entry point group is queried (no module is installed yet)."""
    assert isinstance(load_modules().keys, tuple)
