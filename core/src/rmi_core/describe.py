"""`describe`: what the platform has, as JSON (PROPOSAL §3.2, §4.3, §5).

One pure function, `describe(loaded)`, turns the loaded module set into a JSON-able dict; it is
served at `GET /api/v1/describe` (`describe_router`) and printed by `rmi describe` (`main`). Tools
and agents ask this instead of reading code. Nothing here is hand-maintained: it is all read from
the manifests, so it cannot drift from what the core actually loaded.

Shape (`describe_version` 1):

- `modules`: each manifest as JSON (callables as dotted names), plus `routes`, mounted under
  `/<key>` by the core (`mount_path`).
- `load_order`, `disabled` (a `uses` that is off, with the reason).
- `seams`: per seam offered: version, provider, `contract` (the module
  `contracts.<key>_<name>.v<major>`, null if none exists yet), `schemas` (one JSON Schema per
  pydantic model in it) and its consumers (`requires` / `uses`, whether satisfied).
- `decisions`: id, title, status, kind of each `docs/decisions/NNNN-*.md` (front matter; `[]` if the
  folder is absent).
- `routes`, `nav`, `link_kinds`, `permissions`, `jobs`: the same facts from every module in
  one flat list, each row tagged with its `module`.
"""

from __future__ import annotations

import argparse
import importlib
import inspect
import json
import re
import sys
from collections.abc import Callable, Iterable, Sequence
from pathlib import Path
from types import ModuleType
from typing import Any, cast

from pydantic import BaseModel, TypeAdapter
from pydantic.dataclasses import is_pydantic_dataclass

from .loader import LoadedModules, load_modules
from .manifest import ModuleManifest, SeamImpl, parse_version
from .resolve import ResolutionError

__all__ = [
    "DESCRIBE_PATH",
    "DECISIONS_DIR",
    "DESCRIBE_VERSION",
    "contract_module_name",
    "describe",
    "describe_router",
    "main",
    "mount_path",
]

DESCRIBE_VERSION = 1
DESCRIBE_PATH = "/api/v1/describe"
DECISIONS_DIR = Path(__file__).resolve().parents[3] / "docs" / "decisions"
_NOT_DECISIONS = ("README.md", "0000-template.md")

type Json = dict[str, Any]
type ContractImporter = Callable[[str], ModuleType]


def mount_path(key: str, path: str) -> str:
    """Where the core mounts a module router's path: `/<key>` + path (routers are relative)."""
    return f"/{key}{path}" if path != "/" else f"/{key}"


def contract_module_name(seam: SeamImpl) -> str:
    """`parts.item_estimate` 1.x -> `contracts.parts_item_estimate.v1` (PROPOSAL §4.3)."""
    return f"contracts.{seam.name.replace('.', '_')}.v{parse_version(seam.version)[0]}"


def _routes(manifest: ModuleManifest) -> list[Json]:
    rows: list[Json] = []
    for router in manifest.routers:
        for route in router.routes:
            path: object = getattr(route, "path", None)
            if not isinstance(path, str):
                continue
            methods = cast("Iterable[object]", getattr(route, "methods", None) or ())
            name: object = getattr(route, "name", None)
            rows.append(
                {
                    "path": mount_path(manifest.key, path),
                    "methods": sorted(str(m) for m in methods),
                    "name": name if isinstance(name, str) else None,
                }
            )
    return sorted(rows, key=lambda r: (r["path"], r["methods"]))


def _schemas(contract: ModuleType) -> Json:
    """One JSON Schema per pydantic model or dataclass defined in the contract module."""
    found: Json = {}
    for name, obj in sorted(vars(contract).items()):
        if not inspect.isclass(obj) or obj.__module__ != contract.__name__:
            continue
        if issubclass(obj, BaseModel) or is_pydantic_dataclass(obj):
            found[name] = TypeAdapter(obj).json_schema()
    return found


def _seam_contract(seam: SeamImpl, importer: ContractImporter) -> Json:
    name = contract_module_name(seam)
    try:
        module = importer(name)
    except ModuleNotFoundError as exc:
        if exc.name is not None and name.startswith(exc.name):  # the contract itself is absent
            return {"contract": None, "contract_error": None, "schemas": {}}
        return {"contract": name, "contract_error": repr(exc), "schemas": {}}
    except Exception as exc:  # describe must still answer; the error is part of the answer
        return {"contract": name, "contract_error": repr(exc), "schemas": {}}
    return {"contract": name, "contract_error": None, "schemas": _schemas(module)}


def _seams(loaded: LoadedModules, importer: ContractImporter) -> list[Json]:
    versions = {impl.name: impl.version for m in loaded.manifests for impl in m.seams_offered}
    rows: list[Json] = []
    for m in loaded.manifests:
        for impl in m.seams_offered:
            consumers: list[Json] = []
            for c in loaded.manifests:
                for how, refs in (("requires", c.requires), ("uses", c.uses)):
                    consumers += [
                        {
                            "module": c.key,
                            "how": how,
                            "range": ref.range,
                            "satisfied": ref.accepts(impl.version),
                        }
                        for ref in refs
                        if ref.name == impl.name
                    ]
            rows.append(
                {
                    "name": impl.name,
                    "version": versions[impl.name],
                    "provider": m.key,
                    "impl": impl.impl_name,
                    **_seam_contract(impl, importer),
                    "consumers": consumers,
                }
            )
    return sorted(rows, key=lambda r: r["name"])


def _flat(loaded: LoadedModules, field: str) -> list[Json]:
    """Rows of one manifest list (`nav`, `jobs`, ...) from every module, tagged with `module`."""
    rows: list[Json] = []
    for m in loaded.manifests:
        dumped: Any = m.model_dump(mode="json")[field]
        rows += [{"module": m.key, **row} for row in dumped]
    return rows


def _permissions(loaded: LoadedModules) -> list[Json]:
    rows: list[Json] = []
    for m in loaded.manifests:
        p = m.permissions
        rows.append(
            {
                "module": m.key,
                "facets": list(p.facets),
                "capabilities": list(p.capabilities),
                "access_keys": [{"key": a.key, "label": a.label} for a in p.access_keys],
                "always_on": p.always_on,
            }
        )
    return rows


def _decisions(folder: Path) -> list[Json]:
    """id (the `NNNN` file prefix), title (first `# ` heading), status and kind (front matter)."""
    if not folder.is_dir():
        return []
    rows: list[Json] = []
    for path in sorted(folder.glob("*.md")):
        if path.name in _NOT_DECISIONS:
            continue
        text = path.read_text(encoding="utf-8")
        block = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
        fields: dict[str, str] = {}
        for line in block.group(1).split("\n") if block else ():
            key, sep, value = line.partition(":")
            if sep and not key.startswith((" ", "-")):
                fields[key.strip()] = value.strip().strip("\"'")
        heading = re.search(r"^# (.+)$", text, re.MULTILINE)
        decision_id = path.stem.split("-", 1)[0]
        title = path.stem
        if heading:
            title = re.sub(rf"^{re.escape(decision_id)}\s*[—–-]\s*", "", heading.group(1).strip())
        rows.append(
            {
                "id": decision_id,
                "title": title,
                "status": fields.get("status"),
                "kind": fields.get("kind"),
            }
        )
    return rows


def describe(
    loaded: LoadedModules,
    *,
    importer: ContractImporter = importlib.import_module,
    decisions_dir: Path = DECISIONS_DIR,
) -> Json:
    """The whole description as a JSON-able dict. `importer` finds seam contract modules;
    `decisions_dir` is the folder of decision records (absent folder: no decisions)."""
    modules: list[Json] = []
    routes: list[Json] = []
    for m in loaded.manifests:
        module_routes = _routes(m)
        modules.append({**m.model_dump(mode="json"), "routes": module_routes})
        routes += [{"module": m.key, **r} for r in module_routes]
    return {
        "describe_version": DESCRIBE_VERSION,
        "load_order": list(loaded.keys),
        "modules": modules,
        "disabled": [
            {"module": d.module, "seam": d.seam, "range": d.range, "reason": d.reason}
            for d in loaded.disabled
        ],
        "seams": _seams(loaded, importer),
        "routes": routes,
        "nav": _flat(loaded, "nav"),
        "link_kinds": _flat(loaded, "links_offered"),
        "permissions": _permissions(loaded),
        "jobs": _flat(loaded, "jobs"),
        "decisions": _decisions(decisions_dir),
    }


def describe_router(
    loaded: LoadedModules, *, importer: ContractImporter = importlib.import_module
) -> Any:
    """A FastAPI router serving `GET /api/v1/describe` for this loaded set (built once)."""
    from fastapi import APIRouter

    document = describe(loaded, importer=importer)
    router = APIRouter()

    @router.get(DESCRIBE_PATH, name="describe")
    def get_describe() -> Json:  # pyright: ignore[reportUnusedFunction]
        return document

    return router


def main(argv: Sequence[str] | None = None) -> int:
    """`rmi describe [--compact]`: print the description as JSON; exit 1 if loading fails."""
    parser = argparse.ArgumentParser(prog="rmi")
    sub = parser.add_subparsers(dest="command", required=True)
    cmd = sub.add_parser("describe", help="print what the platform has, as JSON")
    cmd.add_argument("--compact", action="store_true", help="one line, no indentation")
    args = parser.parse_args(argv)
    try:
        document = describe(load_modules())
    except ResolutionError as exc:
        for problem in exc.problems:
            print(problem, file=sys.stderr)
        return 1
    print(json.dumps(document, indent=None if args.compact else 2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
