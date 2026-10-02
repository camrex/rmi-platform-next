"""Resolution: manifests -> load order (PROPOSAL §3.2, docs/CONTRACT.md). A pure function.

Checks across manifests, which the single-manifest model cannot do:

- duplicate module keys and duplicate seam offers are rejected;
- a `requires` nobody offers (or offers in a version outside the range) fails, naming the module,
  the seam and the range;
- a `uses` that is absent (or out of range) does not fail: the feature is disabled and a reason
  is returned;
- `core_revision`, when the caller passes the core's revision, must contain it;
- dependency cycles (through `requires` or through a `uses` that is satisfied) are rejected.

Providers come before their consumers; ties break by key, so the order is deterministic.
Every problem found is reported in one `ResolutionError`, not just the first.
"""

from __future__ import annotations

import heapq
from collections.abc import Sequence
from dataclasses import dataclass

from .manifest import ModuleManifest, range_contains

__all__ = ["DisabledFeature", "Resolution", "ResolutionError", "resolve"]


class ResolutionError(ValueError):
    """Resolution failed; `problems` lists every reason, one line each."""

    def __init__(self, problems: Sequence[str]) -> None:
        self.problems: tuple[str, ...] = tuple(problems)
        super().__init__("; ".join(self.problems))


@dataclass(frozen=True)
class DisabledFeature:
    """A `uses` that is not satisfied: the module still loads, the feature is off."""

    module: str
    seam: str
    range: str
    reason: str


@dataclass(frozen=True)
class Resolution:
    """`load_order`: module keys, providers first. `disabled`: unsatisfied `uses`.
    `providers`: seam name -> key of the module offering it."""

    load_order: tuple[str, ...]
    disabled: tuple[DisabledFeature, ...]
    providers: dict[str, str]


def resolve(manifests: Sequence[ModuleManifest], *, core_revision: str | None = None) -> Resolution:
    """Resolve manifests into a load order, or raise `ResolutionError` naming every problem."""
    problems: list[str] = []

    by_key: dict[str, ModuleManifest] = {}
    for m in manifests:
        if m.key in by_key:
            problems.append(f"duplicate module key {m.key!r}")
        else:
            by_key[m.key] = m

    offers: dict[str, tuple[str, str]] = {}  # seam -> (module key, version)
    for m in by_key.values():
        for impl in m.seams_offered:
            if impl.name in offers:
                problems.append(
                    f"seam {impl.name!r} is offered by both {offers[impl.name][0]!r} and {m.key!r}"
                )
            else:
                offers[impl.name] = (m.key, impl.version)

    after: dict[str, set[str]] = {key: set() for key in by_key}  # key -> providers it follows
    disabled: list[DisabledFeature] = []

    for m in by_key.values():
        if (
            core_revision is not None
            and m.core_revision is not None
            and not range_contains(m.core_revision, core_revision)
        ):
            problems.append(
                f"module {m.key!r} needs core revision {m.core_revision!r}, "
                f"but core is at {core_revision!r}"
            )
        for ref in m.requires:
            if ref.name not in offers:
                problems.append(
                    f"module {m.key!r} requires seam {ref.name!r} {ref.range!r}, "
                    "but no loaded module offers it"
                )
            elif not ref.accepts(offers[ref.name][1]):
                provider, version = offers[ref.name]
                problems.append(
                    f"module {m.key!r} requires seam {ref.name!r} {ref.range!r}, "
                    f"but {provider!r} offers version {version!r}"
                )
            else:
                after[m.key].add(offers[ref.name][0])
        for ref in m.uses:
            if ref.name not in offers:
                reason = f"no loaded module offers seam {ref.name!r}"
            elif not ref.accepts(offers[ref.name][1]):
                provider, version = offers[ref.name]
                reason = (
                    f"{provider!r} offers seam {ref.name!r} version {version!r}, "
                    f"outside {ref.range!r}"
                )
            else:
                after[m.key].add(offers[ref.name][0])
                continue
            disabled.append(DisabledFeature(m.key, ref.name, ref.range, reason))

    order, stuck = _sort(after)
    if stuck:
        problems.append("dependency cycle among modules: " + ", ".join(repr(k) for k in stuck))

    if problems:
        raise ResolutionError(problems)
    return Resolution(
        load_order=order,
        disabled=tuple(disabled),
        providers={seam: key for seam, (key, _) in offers.items()},
    )


def _sort(after: dict[str, set[str]]) -> tuple[tuple[str, ...], list[str]]:
    """Topological order (smallest key first among the ready); the keys left over if cyclic."""
    waiting = {key: set(deps) for key, deps in after.items()}
    ready = [key for key, deps in waiting.items() if not deps]
    heapq.heapify(ready)
    order: list[str] = []
    while ready:
        key = heapq.heappop(ready)
        order.append(key)
        for other, deps in waiting.items():
            if key in deps:
                deps.discard(key)
                if not deps:
                    heapq.heappush(ready, other)
    return tuple(order), sorted(key for key in waiting if key not in order)
