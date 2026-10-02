"""The module contract: one typed manifest per module (PROPOSAL §3.2, docs/CONTRACT.md).

A module is found through the `rmi.modules` entry point and hands the core one
`ModuleManifest`. Anything the manifest does not declare, the module does not get: no route,
nav item, permission, GIS slot, job, event handler, link kind, card or seam exists for the core
unless it is named here. The core never imports a module for any other reason.

Everything is strict (no coercion: `"1"` is not `1`), closed (unknown fields are errors) and
frozen. Lists are accepted and stored as tuples. Callables (routers, jobs, handlers, seam
implementations) are excluded from the JSON form; `describe` shows their dotted names instead.

The parts are pydantic dataclasses so a manifest reads as in the proposal:
`SeamRef("catalog.items", ">=1,<2")`, `Nav("Pages", "/hello/pages")`.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from typing import Annotated, Any, Literal, Protocol, runtime_checkable

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, computed_field, model_validator
from pydantic.dataclasses import dataclass
from pydantic.json_schema import SkipJsonSchema

__all__ = [
    "Accent",
    "AccessKey",
    "Card",
    "CatalogRef",
    "GisFeature",
    "Job",
    "LinkKind",
    "ModuleManifest",
    "Nav",
    "OidFrame",
    "On",
    "Owned",
    "Permissions",
    "Relation",
    "Router",
    "SeamImpl",
    "SeamRef",
    "Slot",
    "parse_range",
    "parse_version",
    "range_contains",
]

_CONFIG = ConfigDict(strict=True, extra="forbid", arbitrary_types_allowed=True)

# ---------------------------------------------------------------------------------------------
# Names and versions
# ---------------------------------------------------------------------------------------------

_KEY = r"^[a-z][a-z0-9_]*$"
_QUALIFIED = r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$"  # <module>.<name>: seams, links, cards
_FACET = r"^[a-z][a-z0-9_]*:[a-z][a-z0-9_]*$"  # verb:noun or module:verb, e.g. edit:inventory
_RESERVED_KEYS = frozenset({"core", "api", "static", "admin", "auth"})

Key = Annotated[str, Field(pattern=_KEY)]
Qualified = Annotated[str, Field(pattern=_QUALIFIED)]
Facet = Annotated[str, Field(pattern=_FACET)]
Label = Annotated[str, Field(min_length=1, max_length=80)]

_VERSION_RE = re.compile(r"^\d+(\.\d+){0,2}$")
_CLAUSE_RE = re.compile(r"^(>=|<=|==|>|<)(\d+(?:\.\d+){0,2})$")


def parse_version(text: str) -> tuple[int, ...]:
    """`"1.2"` -> `(1, 2)`. Up to three numeric parts; leading zeros allowed (`"0005"`)."""
    if not _VERSION_RE.match(text):
        raise ValueError(f"version {text!r}: expected MAJOR[.MINOR[.PATCH]], digits only")
    return tuple(int(part) for part in text.split("."))


def parse_range(text: str) -> tuple[tuple[str, tuple[int, ...]], ...]:
    """`">=1,<2"` -> `((">=", (1,)), ("<", (2,)))`. Every clause must hold (AND)."""
    clauses: list[tuple[str, tuple[int, ...]]] = []
    for raw in text.split(","):
        match = _CLAUSE_RE.match(raw.strip())
        if match is None:
            raise ValueError(
                f"version range {text!r}: clause {raw.strip()!r} is not <op><version>, "
                "op one of >= > <= < =="
            )
        clauses.append((match.group(1), parse_version(match.group(2))))
    return tuple(clauses)


def _pad(a: tuple[int, ...], b: tuple[int, ...]) -> tuple[tuple[int, ...], tuple[int, ...]]:
    width = max(len(a), len(b))
    return a + (0,) * (width - len(a)), b + (0,) * (width - len(b))


def range_contains(range_text: str, version: str) -> bool:
    """True when `version` satisfies every clause of `range_text` (`"1.4"` in `">=1,<2"`)."""
    have = parse_version(version)
    for op, bound in parse_range(range_text):
        left, right = _pad(have, bound)
        ok = {
            ">=": left >= right,
            ">": left > right,
            "<=": left <= right,
            "<": left < right,
            "==": left == right,
        }[op]
        if not ok:
            return False
    return True


def _check_version(text: str) -> str:
    parse_version(text)
    return text


def _check_range(text: str) -> str:
    parse_range(text)
    return text


Version = Annotated[str, AfterValidator(_check_version)]
VersionRange = Annotated[str, AfterValidator(_check_range)]


def _as_tuple(value: Sequence[Any]) -> tuple[Any, ...]:
    return tuple(value)


type Many[T] = Annotated[Sequence[T], AfterValidator(_as_tuple)]
"""A list or tuple on the way in, always a tuple once validated (manifests are frozen)."""

type Fn = SkipJsonSchema[Callable[..., Any]]


def _dotted(obj: object) -> str:
    module = getattr(obj, "__module__", None) or type(obj).__module__
    name = getattr(obj, "__qualname__", None) or type(obj).__qualname__
    return f"{module}.{name}"


def _unique(what: str, names: Sequence[str]) -> None:
    seen: set[str] = set()
    for name in names:
        if name in seen:
            raise ValueError(f"duplicate {what} {name!r}")
        seen.add(name)


# ---------------------------------------------------------------------------------------------
# Parts
# ---------------------------------------------------------------------------------------------


Accent = Literal[
    "blue", "violet", "green", "orange", "cyan", "teal", "red", "amber", "pink", "slate"
]
"""The module's one hue in the shell (replaces the colour table in the old `chrome.py`)."""


@runtime_checkable
class Router(Protocol):
    """Anything with `routes` (a FastAPI `APIRouter`); the core mounts it, nothing else does."""

    @property
    def routes(self) -> Sequence[object]: ...


@dataclass(frozen=True, config=_CONFIG)
class SeamRef:
    """A seam this module consumes, and the versions of it this module accepts."""

    name: Qualified
    range: VersionRange

    def accepts(self, version: str) -> bool:
        return range_contains(self.range, version)


@dataclass(frozen=True, config=_CONFIG)
class SeamImpl:
    """A seam this module offers: its name, the version it implements, the implementation."""

    name: Qualified
    version: Version
    impl: SkipJsonSchema[object] = Field(exclude=True)

    @computed_field
    @property
    def impl_name(self) -> str:
        return _dotted(self.impl)


@dataclass(frozen=True, config=_CONFIG)
class AccessKey:
    """A permission that is not a place: a key with roles but no pages (e.g. a finance key)."""

    key: Key
    label: Label


@dataclass(frozen=True, config=_CONFIG)
class Permissions:
    """What may be granted on this module, beyond the core's project x module role."""

    facets: Many[Facet] = ()
    capabilities: Many[Qualified] = ()
    access_keys: Many[AccessKey] = ()
    always_on: bool = False

    def __post_init__(self) -> None:
        _unique("facet", self.facets)
        _unique("capability", self.capabilities)
        _unique("access key", [a.key for a in self.access_keys])


@dataclass(frozen=True, config=_CONFIG)
class Nav:
    """One entry in the shell's module navigation, under the module's own path."""

    label: Label
    path: Annotated[str, Field(pattern=r"^/[a-z0-9_\-/{}]*$")]
    facet: Facet | None = None
    order: int = 100


@dataclass(frozen=True, config=_CONFIG)
class Slot:
    """A GIS dataset this module reads (one fetch per layer, core-owned sync, ADR 0023)."""

    key: Key
    dataset: Key
    required: bool = False
    writable_fields: Many[Key] = ()
    identity: Literal["globalid", "objectid"] = "globalid"

    def __post_init__(self) -> None:
        _unique(f"writable field in slot {self.key!r}", self.writable_fields)


_CRON_FIELD = r"[0-9*/,\-]+"
_CRON = rf"^{_CRON_FIELD}( {_CRON_FIELD}){{4}}$"


@dataclass(frozen=True, config=_CONFIG)
class Job:
    """A background task; with `cron`, also a schedule (five fields, UTC)."""

    fn: Fn = Field(exclude=True)
    cron: Annotated[str, Field(pattern=_CRON)] | None = None

    @computed_field
    @property
    def name(self) -> str:
        return _dotted(self.fn)


@dataclass(frozen=True, config=_CONFIG)
class On:
    """An event handler: `event` (`<namespace>.<verb>`), optional subject filter, handler."""

    event: Qualified
    subject: Key | None
    handler: Fn = Field(exclude=True)

    @computed_field
    @property
    def handler_name(self) -> str:
        return _dotted(self.handler)


@dataclass(frozen=True, config=_CONFIG)
class GisFeature:
    """Identity: a feature in a synced dataset, keyed by GlobalID (`gis:<dataset>:<id>`)."""

    dataset: Key
    kind: Literal["gis"] = "gis"


@dataclass(frozen=True, config=_CONFIG)
class OidFrame:
    """Identity: a row of an OID layer, keyed by OBJECTID (`oid:<dataset>:<id>`)."""

    dataset: Key
    kind: Literal["oid"] = "oid"


@dataclass(frozen=True, config=_CONFIG)
class Owned:
    """Identity: a record the module owns (`<module>.<kind>:<id>`)."""

    kind: Literal["owned"] = "owned"


Identity = Annotated[GisFeature | OidFrame | Owned, Field(discriminator="kind")]


@dataclass(frozen=True, config=_CONFIG)
class LinkKind:
    """A kind of thing other modules may link to; `route` is a template with `{id}`."""

    name: Qualified
    identity: Identity
    route: Annotated[str, Field(pattern=r"^/[a-z0-9_\-/]*\{id\}[a-z0-9_\-/]*$")]
    label: Label
    permission: Facet | None = None


@dataclass(frozen=True, config=_CONFIG)
class Relation:
    """`from_kind` -> `to_kind`: the resolver maps a ref of one to refs of the other."""

    from_kind: Qualified
    to_kind: Qualified
    resolver: Fn = Field(exclude=True)

    @computed_field
    @property
    def resolver_name(self) -> str:
        return _dotted(self.resolver)


@dataclass(frozen=True, config=_CONFIG)
class Card:
    """A link that renders inline on another module's page (PROPOSAL §4.4)."""

    name: Qualified
    route: Annotated[str, Field(pattern=r"^/[a-z0-9_\-/{}]*$")]
    accepts: Many[Qualified]
    grant: Literal["host", "own"] = "own"


@dataclass(frozen=True, config=_CONFIG)
class CatalogRef:
    """A column in this module's schema holding a catalog item id ("who points at me", §7.5)."""

    table: Qualified
    column: Key


# ---------------------------------------------------------------------------------------------
# The manifest
# ---------------------------------------------------------------------------------------------


class ModuleManifest(BaseModel):
    """Everything a module is, to the core. See docs/CONTRACT.md for each field."""

    model_config = ConfigDict(
        strict=True, extra="forbid", frozen=True, arbitrary_types_allowed=True
    )

    key: Key
    version: Version
    display_name: Label
    accent: Accent
    description: str = ""
    docs: str = "README.md"

    requires: Many[SeamRef] = ()
    uses: Many[SeamRef] = ()

    db_schema: Key | None = None
    migrations: str | None = None
    core_revision: VersionRange | None = None

    routers: SkipJsonSchema[Many[Router]] = Field(default=(), exclude=True)
    permissions: Permissions = Permissions()
    nav: Many[Nav] = ()
    gis: Many[Slot] = ()
    jobs: Many[Job] = ()
    on: Many[On] = ()

    links_offered: Many[LinkKind] = ()
    relations: Many[Relation] = ()
    cards_offered: Many[Card] = ()
    cards_hosted: Many[Qualified] = ()
    seams_offered: Many[SeamImpl] = ()
    catalog_refs: Many[CatalogRef] = ()

    validation: Fn | None = Field(default=None, exclude=True)

    @computed_field
    @property
    def router_count(self) -> int:
        return len(self.routers)

    @model_validator(mode="after")
    def _coherent(self) -> ModuleManifest:
        self._check_names()
        self._check_paths()
        self._check_seams()
        self._check_permissions()
        self._check_storage()
        return self

    def _own(self, what: str, names: Sequence[str]) -> None:
        for name in names:
            if not name.startswith(f"{self.key}."):
                raise ValueError(f"{what} {name!r} must be named {self.key}.<name>")

    def _check_names(self) -> None:
        if self.key in _RESERVED_KEYS:
            raise ValueError(f"module key {self.key!r} is reserved")
        self._own("seam offered", [s.name for s in self.seams_offered])
        self._own("link kind", [k.name for k in self.links_offered])
        self._own("card offered", [c.name for c in self.cards_offered])
        _unique("seam offered", [s.name for s in self.seams_offered])
        _unique("link kind", [k.name for k in self.links_offered])
        _unique("card offered", [c.name for c in self.cards_offered])
        _unique("card hosted", self.cards_hosted)
        _unique("GIS slot", [s.key for s in self.gis])
        _unique("job", [j.name for j in self.jobs])
        _unique("catalog ref", [f"{c.table}.{c.column}" for c in self.catalog_refs])

    def _check_paths(self) -> None:
        prefix = f"/{self.key}"
        paths = [n.path for n in self.nav] + [k.route for k in self.links_offered]
        paths += [c.route for c in self.cards_offered]
        for path in paths:
            if path != prefix and not path.startswith(prefix + "/"):
                raise ValueError(f"path {path!r} must be under {prefix}/")
        _unique("nav path", [n.path for n in self.nav])

    def _check_seams(self) -> None:
        required = {s.name for s in self.requires}
        used = {s.name for s in self.uses}
        _unique("required seam", [s.name for s in self.requires])
        _unique("used seam", [s.name for s in self.uses])
        both = required & used
        if both:
            raise ValueError(f"seam {sorted(both)[0]!r} is in both requires and uses")
        own = {s.name for s in self.seams_offered}
        for name in (required | used) & own:
            raise ValueError(f"module {self.key!r} consumes its own seam {name!r}")

    def _check_permissions(self) -> None:
        facets = set(self.permissions.facets)
        wanted = [n.facet for n in self.nav] + [k.permission for k in self.links_offered]
        for facet in wanted:
            if facet is not None and facet not in facets:
                raise ValueError(f"facet {facet!r} is used but not declared in permissions")
        writes = [s.key for s in self.gis if s.writable_fields]
        if writes and "gis.write_back" not in self.permissions.capabilities:
            raise ValueError(
                f"slot {writes[0]!r} has writable_fields; declare capability 'gis.write_back'"
            )

    def _check_storage(self) -> None:
        if (self.db_schema is None) != (self.migrations is None):
            raise ValueError("db_schema and migrations are declared together or not at all")
        if self.core_revision is not None and self.db_schema is None:
            raise ValueError("core_revision needs db_schema and migrations")
        for ref in self.catalog_refs:
            if self.db_schema is None or not ref.table.startswith(f"{self.db_schema}."):
                raise ValueError(
                    f"catalog ref {ref.table!r} must be a table in this module's schema "
                    f"({self.db_schema!r})"
                )
