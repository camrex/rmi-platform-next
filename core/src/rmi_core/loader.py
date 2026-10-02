"""Module loading: discover and resolve manifests (PROPOSAL §3.2, docs/CONTRACT.md)."""

from __future__ import annotations

from importlib.metadata import entry_points

from .manifest import ModuleManifest
from .resolve import Resolution, resolve

__all__ = ["load_modules"]


def load_modules(core_revision: str | None = None) -> tuple[Resolution, dict[str, ModuleManifest]]:
    """Discover manifests via `rmi.modules` entry points, resolve them, and return the result."""
    eps = entry_points(group="rmi.modules")
    manifests: list[ModuleManifest] = []
    for ep in eps:
        manifest = ep.load()
        if not isinstance(manifest, ModuleManifest):
            raise TypeError(
                f"Entry point {ep.name} did not return a ModuleManifest, got {type(manifest)}"
            )
        manifests.append(manifest)

    resolution = resolve(manifests, core_revision=core_revision)
    return resolution, {m.key: m for m in manifests}
