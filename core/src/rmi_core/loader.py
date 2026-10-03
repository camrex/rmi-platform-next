"""Module loading: the one function `app.py` and `worker.py` both call (PROPOSAL §3.2).

Manifests are found through the `rmi.modules` entry point group; each entry point's name is the
module key and it loads to a `ModuleManifest`. They are resolved (`resolve.py`) and returned in
load order. Two roots (web and worker) calling this one function is what keeps a module from being
registered in one and never firing in the other.
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib.metadata import entry_points

from .manifest import ModuleManifest
from .resolve import DisabledFeature, Resolution, ResolutionError, resolve

__all__ = ["ENTRY_POINT_GROUP", "LoadedModules", "load_modules"]

ENTRY_POINT_GROUP = "rmi.modules"


@dataclass(frozen=True)
class LoadedModules:
    """The loaded set. `manifests` is in load order (providers first)."""

    manifests: tuple[ModuleManifest, ...]
    resolution: Resolution

    @property
    def keys(self) -> tuple[str, ...]:
        return self.resolution.load_order

    @property
    def disabled(self) -> tuple[DisabledFeature, ...]:
        return self.resolution.disabled

    def get(self, key: str) -> ModuleManifest | None:
        return next((m for m in self.manifests if m.key == key), None)


def load_modules(*, core_revision: str | None = None) -> LoadedModules:
    """Discover manifests, resolve them, return the loaded set.

    Raises `ResolutionError` if an entry point cannot be loaded, is not a `ModuleManifest`, or is
    named differently from its manifest's key, and for every problem `resolve` finds.
    """
    manifests: list[ModuleManifest] = []
    problems: list[str] = []
    for ep in entry_points(group=ENTRY_POINT_GROUP):
        try:
            loaded: object = ep.load()
        except Exception as exc:  # a broken module must name itself, not crash the root
            problems.append(f"entry point '{ep.name}' failed to load: {exc!r}")
            continue
        if not isinstance(loaded, ModuleManifest):
            problems.append(
                f"entry point '{ep.name}' did not return a ModuleManifest, "
                f"got {type(loaded).__name__}"
            )
        elif loaded.key != ep.name:
            problems.append(f"entry point '{ep.name}' returned a manifest with key '{loaded.key}'")
        else:
            manifests.append(loaded)
    if problems:
        raise ResolutionError(problems)

    resolution = resolve(manifests, core_revision=core_revision)
    by_key = {m.key: m for m in manifests}
    return LoadedModules(tuple(by_key[k] for k in resolution.load_order), resolution)
