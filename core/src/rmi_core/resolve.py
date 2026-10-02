from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Sequence

from .manifest import ModuleManifest, SeamRef


@dataclass(frozen=True)
class Resolution:
    """The result of resolving module dependencies.
    
    Attributes:
        load_order: The order in which modules should be loaded (providers first).
        disabled: A sequence of (module, seam, reason) for disabled features.
    """

    load_order: tuple[str, ...]
    disabled: tuple[tuple[str, str, str], ...]


def resolve(manifests: Sequence[ModuleManifest]) -> Resolution:
    """Resolve module manifests into a load order and a list of disabled features.

    If duplicate keys or cycles are detected, or if a required seam is unsatisfied,
    this function raises ValueError.

    Args:
        manifests: The manifests of all available modules.

    Returns:
        The resolution containing the load order and disabled features.
    """
    # 1. Duplicate keys
    keys = [m.key for m in manifests]
    if len(keys) != len(set(keys)):
        seen = set()
        for k in keys:
            if k in seen:
                raise ValueError(f"duplicate module key {k!r}")
            seen.add(k)

    # 2. Map seams to providing modules
    seams_provided: dict[str, tuple[str, str]] = {}  # seam_name -> (module_key, version)
    for m in manifests:
        for s in m.seams_offered:
            if s.name in seams_provided:
                prov_mod, _ = seams_provided[s.name]
                raise ValueError(f"duplicate seam {s.name!r} provided by {m.key!r} and {prov_mod!r}")
            seams_provided[s.name] = (m.key, s.version)

    # 3. Build graph and check requires/uses
    adj: dict[str, set[str]] = {m.key: set() for m in manifests}
    disabled: list[tuple[str, str, str]] = []

    for m in manifests:
        # Process requires
        for req in m.requires:
            if req.name not in seams_provided:
                raise ValueError(
                    f"module {m.key!r} requires seam {req.name!r} (range {req.range!r}), "
                    f"but no module provides it"
                )

            prov_mod, prov_ver = seams_provided[req.name]
            if not req.accepts(prov_ver):
                raise ValueError(
                    f"module {m.key!r} requires seam {req.name!r} (range {req.range!r}), "
                    f"but {prov_mod!r} provides incompatible version {prov_ver!r}"
                )

            adj[m.key].add(prov_mod)

        # Process uses
        for use in m.uses:
            if use.name not in seams_provided:
                disabled.append((m.key, use.name, "no module provides this seam"))
                continue

            prov_mod, prov_ver = seams_provided[use.name]
            if not use.accepts(prov_ver):
                disabled.append(
                    (m.key, use.name, f"{prov_mod!r} provides incompatible version {prov_ver!r}")
                )
                continue

            adj[m.key].add(prov_mod)

    # 4. Cycle detection and topological sort (Kahn's algorithm)
    in_degree = {m.key: 0 for m in manifests}
    out_adj: dict[str, set[str]] = {m.key: set() for m in manifests}
    for u, vs in adj.items():
        for v in vs:
            out_adj[v].add(u)
            in_degree[u] += 1

    queue = deque([k for k, deg in in_degree.items() if deg == 0])
    load_order: list[str] = []

    while queue:
        v = queue.popleft()
        load_order.append(v)
        for u in out_adj[v]:
            in_degree[u] -= 1
            if in_degree[u] == 0:
                queue.append(u)

    if len(load_order) != len(manifests):
        raise ValueError("circular dependency detected in module manifests")

    return Resolution(tuple(load_order), tuple(disabled))
