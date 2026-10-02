"""The module contract (PROPOSAL §3.2, docs/CONTRACT.md): a good manifest validates, bad ones fail
with a message that names what is wrong. Module keys here are invented; core names no real module.
"""

import json
from typing import Any

import pytest
from pydantic import ValidationError

from rmi_core.manifest import (
    AccessKey,
    Card,
    CatalogRef,
    GisFeature,
    Job,
    LinkKind,
    ModuleManifest,
    Nav,
    On,
    Owned,
    Permissions,
    Relation,
    SeamImpl,
    SeamRef,
    Slot,
    parse_range,
    range_contains,
)


class _Router:
    routes: list[object] = []


def _task() -> None: ...


def _resolve(ref: str) -> list[str]:
    return [ref]


def _good(**changes: Any) -> dict[str, Any]:
    fields: dict[str, Any] = {
        "key": "shed",
        "version": "1.0",
        "display_name": "Equipment Sheds",
        "accent": "teal",
        "requires": [SeamRef("parts.items", ">=1,<2")],
        "uses": [SeamRef("planner.phase", ">=1,<2")],
        "db_schema": "shed",
        "migrations": "shed/migrations",
        "core_revision": ">=0005",
        "routers": [_Router()],
        "permissions": Permissions(
            facets=["edit:inventory"],
            capabilities=["gis.write_back"],
            access_keys=[AccessKey("shedfin", "Shed finance")],
        ),
        "nav": [Nav("Sheds", "/shed/sheds", facet="edit:inventory")],
        "gis": [Slot("shed", dataset="sheds", required=True, writable_fields=["rel_track"])],
        "jobs": [Job(_task, cron="0 3 * * *")],
        "on": [On("dataset.landed", "sheds", _task)],
        "links_offered": [
            LinkKind("shed.shed", GisFeature("sheds"), "/shed/sheds/{id}", "Shed"),
            LinkKind("shed.note", Owned(), "/shed/notes/{id}", "Note"),
        ],
        "relations": [Relation("shed.shed", "viewer.pano", _resolve)],
        "cards_offered": [Card("shed.summary", "/shed/cards/summary", accepts=["shed.shed"])],
        "cards_hosted": ["viewer.pano"],
        "seams_offered": [SeamImpl("shed.estimate", "1.0", impl=_task)],
        "catalog_refs": [CatalogRef("shed.instance", column="item_id")],
        "validation": _task,
    }
    fields.update(changes)
    return fields


def test_good_manifest_validates_and_freezes() -> None:
    m = ModuleManifest(**_good())
    assert m.requires == (SeamRef("parts.items", ">=1,<2"),)
    assert isinstance(m.nav, tuple)
    with pytest.raises(ValidationError):
        m.key = "other"  # type: ignore[misc]


def test_minimal_manifest_needs_only_identity() -> None:
    m = ModuleManifest(key="tiny", version="0.1", display_name="Tiny", accent="slate")
    assert m.routers == () and m.permissions == Permissions() and m.db_schema is None


def test_json_form_names_callables_and_omits_them() -> None:
    dumped = ModuleManifest(**_good()).model_dump(mode="json")
    json.dumps(dumped)  # serialisable: `describe` serves exactly this
    assert dumped["jobs"][0]["name"].endswith("test_manifest._task")
    assert "fn" not in dumped["jobs"][0]
    assert "routers" not in dumped and dumped["router_count"] == 1
    assert dumped["seams_offered"][0]["impl_name"].endswith("_task")
    assert dumped["links_offered"][0]["identity"] == {"dataset": "sheds", "kind": "gis"}


def test_json_schema_is_generated() -> None:
    schema = ModuleManifest.model_json_schema(mode="serialization")
    assert "key" in schema["required"] and "routers" not in schema["properties"]


@pytest.mark.parametrize(
    ("range_text", "version", "ok"),
    [
        (">=1,<2", "1.0", True),
        (">=1,<2", "1.9.3", True),
        (">=1,<2", "2.0", False),
        (">=1.2", "1.1", False),
        ("==1.0", "1", True),
        (">=0005", "0006", True),
    ],
)
def test_version_ranges(range_text: str, version: str, ok: bool) -> None:
    assert range_contains(range_text, version) is ok
    assert SeamRef("parts.items", range_text).accepts(version) is ok


@pytest.mark.parametrize("bad", ["", ">=1,", "~1", "1", ">=1.x", ">= 1 <2", ">=1.2.3.4"])
def test_bad_ranges_rejected(bad: str) -> None:
    with pytest.raises(ValueError):
        parse_range(bad)
    with pytest.raises(ValidationError):
        SeamRef("parts.items", bad)


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"key": "Shed"}, "pattern"),
        ({"key": "core"}, "reserved"),
        ({"version": "v1"}, "MAJOR"),
        ({"version": 1}, "string"),  # strict: no coercion
        ({"accent": "puce"}, "accent"),
        ({"colour": "teal"}, "Extra inputs"),
        ({"requires": [{"name": "parts.items", "range": ">=1"}]}, "SeamRef"),
        ({"requires": [SeamRef("a.b", ">=1"), SeamRef("a.b", ">=1")]}, "duplicate required"),
        ({"uses": [SeamRef("parts.items", ">=1")]}, "both requires and uses"),
        ({"uses": [SeamRef("shed.estimate", ">=1")]}, "consumes its own seam"),
        ({"seams_offered": [SeamImpl("other.estimate", "1.0", impl=_task)]}, "shed.<name>"),
        ({"nav": [Nav("Elsewhere", "/other/x")]}, "must be under /shed/"),
        ({"nav": [Nav("Sheds", "/shed/s", facet="edit:roofs")]}, "not declared"),
        ({"gis": [Slot("a", "x"), Slot("a", "y")]}, "duplicate GIS slot"),
        ({"permissions": Permissions(facets=["edit:inventory"])}, "gis.write_back"),
        ({"migrations": None}, "together"),
        ({"catalog_refs": [CatalogRef("elsewhere.instance", "item_id")]}, "this module's schema"),
        ({"routers": [object()]}, "Router"),
        ({"cards_hosted": "viewer.pano"}, "not allowed as a Sequence"),
    ],
)
def test_bad_manifests_rejected(changes: dict[str, Any], message: str) -> None:
    with pytest.raises((ValidationError, ValueError), match=message):
        ModuleManifest(**_good(**changes))


def test_parts_reject_bad_input() -> None:
    with pytest.raises(ValidationError, match="pattern"):
        LinkKind("shed.shed", GisFeature("sheds"), "/shed/sheds", "Shed")  # no {id}
    with pytest.raises(ValidationError):
        Slot("s", "sheds", identity="guid")  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        Card("shed.c", "/shed/c", accepts=["shed.shed"], grant="anyone")  # type: ignore[arg-type]
    with pytest.raises(ValidationError, match="duplicate facet"):
        Permissions(facets=["edit:x", "edit:x"])
    with pytest.raises(ValidationError, match="pattern"):
        Job(_task, cron="daily")
    with pytest.raises(ValidationError):
        Nav("Sheds", "/shed", order="1")  # type: ignore[arg-type]
