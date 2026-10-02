# The module contract

A module hands the core one `ModuleManifest` (`core/src/rmi_core/manifest.py`), found through the
`rmi.modules` entry point. **Anything the manifest does not declare, the module does not get**: the
core mounts no route, shows no nav item, grants no facet, syncs no dataset, runs no job, calls no
handler, offers no link, card or seam that is not named here. Design: PROPOSAL §3.2, §4.

Rules for every field: strict types (no coercion, `"1"` is not `1`), unknown fields are errors, the
manifest is frozen, lists are stored as tuples. Callables are kept out of the JSON form; `describe`
shows their dotted names. Names other modules see are `<key>.<name>` and must start with the
module's own key; paths must start with `/<key>/`.

## Identity

| field | means | gets the module |
|---|---|---|
| `key` | `^[a-z][a-z0-9_]*$`, not `core`, `api`, `static`, `admin`, `auth` | its URL prefix `/<key>/`, its name space for seams, links, cards |
| `version` | `MAJOR[.MINOR[.PATCH]]` | shown by `describe` |
| `display_name`, `accent`, `description` | launcher label, one hue from a closed list, blurb | a launcher card and badge; no colour table in the core |
| `docs` | the module's one-page README | linked from `describe` |

## Dependencies on other modules: seams only

| field | means | gets the module |
|---|---|---|
| `requires: SeamRef(name, range)` | a seam it cannot run without, e.g. `SeamRef("catalog.items", ">=1,<2")` | start-up **fails** naming module and range if no loaded module offers a matching version |
| `uses: SeamRef(name, range)` | a seam that turns a feature on | the feature is **off, with a reason**, when absent; the module still loads |
| `seams_offered: SeamImpl(name, version, impl)` | an implementation of a contract in `contracts/<key>_<name>/v<major>.py` | `seams.get(Contract)` returns `impl` to consumers whose range accepts `version` |

A range is comma-separated clauses, all of which must hold: `>=`, `>`, `<=`, `<`, `==` and a version
(`">=1,<2"`). A seam may not be both required and used, and a module may not consume its own seam.
Modules never import each other; a seam, a link or a card is the only way across.

## Storage

| field | means | gets the module |
|---|---|---|
| `db_schema`, `migrations` | its Postgres schema and Alembic chain (declared together) | the chain run at deploy and from scratch in tests (`docs/TESTING.md`) |
| `core_revision` | the core migration range it was written against | start-up fails when core is outside it |
| `catalog_refs: CatalogRef(table, column)` | a column in its own schema holding a catalog item id | catalog merge and delete carry or block on it ("who points at me", §7.5) |

## Web, permissions, work

| field | means | gets the module |
|---|---|---|
| `routers` | FastAPI routers (anything with `routes`) | mounted under `/<key>/` by the core, in both app roots |
| `nav: Nav(label, path, facet?, order)` | shell navigation entries under `/<key>/` | shown to users who hold `facet` (if set) |
| `permissions: Permissions(facets, capabilities, access_keys, always_on)` | `facets` are editor rights (`edit:inventory`); `capabilities` are dangerous powers (`gis.write_back`); `access_keys` are keys with roles but no pages; `always_on` cannot be disabled per project | grantable in the access admin; any facet used by `nav` or a `LinkKind` must be declared here |
| `jobs: Job(fn, cron?)` | a background task, optionally scheduled (five-field cron, UTC) | enqueued and scheduled by the worker, which reads the same manifest as the web app |
| `on: On(event, subject?, handler)` | handler for a core event (`dataset.landed`, `phase.changed`, `link.changed`, `catalog.classified`, `price.superseded`, `snapshot.sealed`), optionally for one subject (dataset) | called, isolated, result recorded |
| `validation` | readiness provider `(session, project, phase) -> report` (ADR 0024) | included in the readiness gate |

## GIS

| field | means | gets the module |
|---|---|---|
| `gis: Slot(key, dataset, required, writable_fields, identity)` | a synced dataset it reads; `identity` is `globalid` (default) or `objectid` (OID layers only) | the dataset synced by the core and readable; `required` blocks readiness when unbound |
| `writable_fields` | attributes it may propose changes to | entries in the deferred change queue (§9.1); needs capability `gis.write_back` |

## Links and cards

| field | means | gets the module |
|---|---|---|
| `links_offered: LinkKind(name, identity, route, label, permission?)` | a kind of thing others may link to; `identity` is `GisFeature(dataset)`, `OidFrame(dataset)` or `Owned()`; `route` contains `{id}` | `links.for_ref` returns links to it, filtered by presence, project enablement and grants |
| `relations: Relation(from_kind, to_kind, resolver)` | "a thing of this kind maps to things of that kind" | its links appear on the other side without either module importing the other |
| `cards_offered: Card(name, route, accepts, grant)` | an inline fragment for refs of the `accepts` kinds; `grant="host"` lets anyone who may see the host page see it | rendered in hosts' card slots |
| `cards_hosted` | cards it shows on its pages | the slot is filled when the offering module is present, empty otherwise |

## Not in the manifest (deliberately)

TIVS asset sub-modules register with TIVS (`AssetModule`, PROPOSAL §8.2), not with the core.
Settings keys and config surfaces arrive with the settings service (phase B2); they will be added
here as fields, not as side registrations. Checks across manifests (a `requires` nobody offers,
duplicate keys, cycles) are `resolve.py`'s job (B1.9), not the model's.
