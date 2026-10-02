# Seams: how today's modules couple, and what a plugin contract must carry

Source: `~/sources/rmi-platform` (paths below are relative to it), read 2026-09-30, plus
`docs/inventory/rmi-platform-issues.md` (cited as "issues §n") for what is planned and not built.
Import edges were counted with grep over `modules/*/src` and `platform-web/src` (tests excluded).
Counts are of import lines, not of call sites.

**Corrected 2026-10-02 (task 0.7b)**: re-read against v1.62.2 (was v1.59.1 plus ADR 0025). RR Audit and the CVS Power Query contract add **no seam**: `SEAM_VERSION` is still 6 (`sbis/seam.py:105`), and the RR-audit code imports nothing from `civ`, `tivs` or `pm`. Counts in §3–§4 below were fixed where wrong; see `changes-since-2026-09-30.md`.

## 1. Summary

- **The core is already clean.** `platform/src/platform_core` imports no module code (grep finds
  only docstrings). Every module→core call is a `register_*` function. The direction is right.
- **The manifest covers about half of what a module is.** `ModuleManifest`
  (`platform/src/platform_core/registry/manifest.py`) carries key, nav, config surfaces, DB schema,
  GIS slots, conversation anchors and alternative slot groups. Routers, sync hooks, validation
  providers, card slots, anchor resolvers, worker tasks, cron jobs, settings tables, access keys and
  the launcher blurb are wired by hand-written calls in eight places (§3). Add a module and you edit
  about nine files outside it.
- **Module↔module coupling is small and shaped as adapters, plus one leak.** Only four seam
  adapters exist (`tivs/sbis_seam.py`, `sbis/pm_seam.py`, `tivs/pm_seam.py`, `cvs/pm_seam.py`), each
  with a version assert. The leak is CIV's web code, imported by SBIS and TIVS (§2.2). Cross-module
  *links* are built as hard-coded URL strings, three ways, with no shared registry.
- **"An absent module leaves no broken links" is done by hand, once per link** (SBIS's
  `_tivs_link_visible`, CIV's `viewer_link`). Nothing checks that a link's target exists.
- **Correction to `docs/inventory/rmi-platform.md`:** it says TIVS does
  `from sbis.models import Bungalow` and queries it. It does not. TIVS imports `sbis` only in
  `tivs/sbis_seam.py:19-23` (`asset_seam`, `crossing_source`, `detector_source`, `estimate`, `seam`);
  13 other TIVS files go through that adapter. The same file says the SBIS→TIVS link is "no ORM FK";
  that is true, but TIVS *does* run SBIS's loaders inside its own session, so the SBIS schema is read
  at run time through SBIS code (§2.1).

## 2. Where the modules couple

### 2.1 Module ↔ module (code imports)

| From → to | Import lines | Where | What crosses | Shape |
|---|---|---|---|---|
| TIVS → SBIS | 5 | `modules/tivs/src/tivs/sbis_seam.py:19-23` | frozen DTOs (`BungalowInventory`, `EquipmentLine`, `UnitPrice`, `AssetEquipment`, `CrossingClassPrices`…), loaders, `project_estimates`, `canonical_globalid` | adapter, `EXPECTED_SEAM_VERSION = 6` vs `sbis.seam.SEAM_VERSION`; import fails on mismatch |
| SBIS → PM | 1 | `modules/sbis/src/sbis/pm_seam.py:19` | one value: project phase (`survey→costing→valuation→delivered`, or None) | adapter, version 1 |
| TIVS → PM | 1 | `modules/tivs/src/tivs/pm_seam.py:17` | same phase | adapter |
| CVS → PM | 1 | `modules/cvs/src/cvs/pm_seam.py:18` | same phase | adapter |
| SBIS → CIV | 4 (2 files) | `sbis/web/pano_card.py:22-30`, `sbis/web/bungalow_map.py:22` | `resolve_asset_pano`, CIV settings, CIV card fragments, `VIEWPOINT_JS`, `PANO_CARD_STYLE` | **direct import of CIV internals and CSS/JS strings**; no adapter, no version |
| TIVS → CIV | 6 (4 files) | `tivs/web/pano_card.py:24-32`, `asset_map.py:22`, `map.py:24`, `asset.py:24` | same | same |
| CIV → SBIS/TIVS | 0 imports | `civ/assets.py:43,76` | URL *templates* `/sbis/bungalows/by-gis/{id}`, `/tivs/map/asset/{slot}/{id}` for marker click-through | hard-coded strings |
| SBIS → TIVS | 0 imports | `sbis/web/asset_cards.py:74-83` | URL built by shape: `/tivs/asset/{process}/{id}?project=`; asset-type→process table (`SG→signal_structure`, `TO→turnout`, `DR→derail`, `XN→xing_equipment`) | hard-coded; comment says "a shared platform deep-link registry is #435's future" |
| TIVS → SBIS | (in adapter) | `tivs/web/sbis_lines.py:172` | URL `/sbis/bungalows/by-gis/{asset_id}` | hard-coded |
| CVS ↔ others | 0 | | shares only the GIS store and the phase | clean |
| PM ↔ SBIS/TIVS/CVS/CIV | 0 imports | | PM owns the phase and property scope; consumers read phase only | clean |

Notes.
- The seam adapters are the good pattern: one import site, re-exported plain data, a version assert
  that fails at import (`tivs/sbis_seam.py:31-35`, `sbis/pm_seam.py:32-36`). But the version is a
  **manual integer** with a human review note in a comment; nothing describes the contract in a form
  a tool or the other side can read.
- The SBIS→TIVS seam is the noisiest one in the issue tracker (issues §3.3): what crosses is decided
  by SBIS code (`sbis.estimate`, `sbis.seam`) and TIVS re-decides per leg; price provenance is lost at
  the crossing (#1434); four divergent `_collapse` normalisers existed (#1054). A plugin contract
  must let the *offering* side declare the type, including provenance, and let the consumer snapshot it.
- The CIV imports run **against** the "modules call services, not each other" story: they are why
  CIV cannot be removed without SBIS and TIVS breaking at import time. The other side of the arrangement
  is deliberate — the card's *routes* live in the host module so the host's access grant gates it
  (`civ/composition.py:34-38`) — but the code is CIV's.
- Cross-schema FKs exist only in migrations (`FROM platform.project`, `modules/tivs/alembic/versions/a7c3f9e25b81…:77,95`);
  ten SBIS migrations and one CIV migration read `platform.`/`sbis.` tables directly. At run time
  modules keep `project_id` as an unconstrained UUID (ADR 0002). A plugin's migrations therefore
  depend on the core schema's tables existing, in order.

### 2.2 Module → core (what every module calls)

Every module's `include_<key>_routers(app)` (`modules/*/src/*/composition.py`) does the same
sequence; this is the de-facto contract:

| Channel | Core API | Called from | In manifest? |
|---|---|---|---|
| Routers | `app.include_router(...)` (SBIS 32, TIVS 35) with an ordering rule (literal path before `{id}`, e.g. `sbis/composition.py:84-89`) | `include_*_routers` | no |
| GIS slots→datasets | `register_gis_datasets(MANIFEST)` (`platform_core/arcgis/datasets.py:70`) | composition **and** `platform_web/worker.py:startup` | slots yes, registration call no |
| Post-sync hooks | `register_sync_hook(dataset, fn)` (`datasets.py:40`); hook `(session, project_id) -> int` runs in a fresh session per hook | SBIS `register_sbis_sync_hooks` (5 halves + per-family), TIVS `register_tivs_sync_hooks`, CVS `register_cvs_sync_hooks`; called from **both** the API and worker roots | no |
| Validation | `register_validation_provider(key, report_fn, rules_fn)` (`validation/registry.py:31`) | SBIS, TIVS | no |
| Conversations | anchors in manifest; `register_anchor_resolver` / `register_anchor_batch_resolver` (`conversations/registry.py:74-80`) | SBIS, TIVS | anchors yes, resolvers no |
| Card slots | `register_card_slot("<module>:<card>", renderer)` (`web/slots.py:62`); renderer `(SlotContext) -> node|None`, run in a SAVEPOINT, exceptions healed to "no card" | SBIS `sbis:contents`, CIV `civ:pano` | no |
| Access | `require_module_access("<key>")` on every route; roles viewer/editor/project_admin (`access/models.py:46`); editor **facets** `edit:inventory/costs/rates/valuation/gis/dax` (`:53`); capabilities `gis.write_back` (`:68`, declared, no consumer) | routes | no |
| Audit | `DbAuditSink.record(AuditEvent)` in the caller's transaction | routes/services | n/a (core service) |
| Worker tasks | none in core; module task functions appended to `WorkerSettings.functions` in `platform_web/worker.py:80-97` wrapped in `instrumented(...)`; cron via `_module_cron_jobs` (`worker.py:55-73`, PM's QBO sync only) | platform_web | no |
| Settings | per-module `*_setting` table + `SETTING_KEYS` list of `SettingKey` (`registry/manifest.py:SettingKey`), consumed by `platform_web/stored_settings.py:31-59` | platform_web | no (only `ConfigSurface`) |
| Analytical API | `APIRouter(prefix="/api/v1/<key>")` per module (`sbis/api.py:39`, `tivs/api.py:40`, `cvs/api.py:42`), PAT-scoped | routers | no |
| DB | schema per module (`db_schema` in manifest), own Alembic chain with own version table `alembic_version_<module>`, `include_name` filter so autogenerate stays in its schema (`modules/tivs/alembic/env.py:48-71`) | `deploy/migrate_remote.sh:50` globs `modules/*/alembic.ini` | schema name yes; chain no |
| Static assets | each module serves its own JS islands via a router (`sbis/web/static_assets.py`, `tivs/web/static_assets.py`, `cvs/web/static_assets.py`) | three near-identical copies | no |

### 2.3 Core/shell → modules (the leaks the "small core" must remove)

`platform_core` (the library) is clean except for **hard-coded module knowledge**:

- `platform_core/web/chrome.py:90-94` — accent colour and label per module key (`sbis`, `tivs`, `civ`, `cvs`, `pm`).
- `platform_core/access/service.py:94,436-441` — `PM_ACCESS_KEYS = ("pmfee","pmfin")`; enabling `pm` enables them; `pm` cannot be disabled.
- `platform_core/access/models.py:53-66` — the facet vocabulary includes SBIS-specific facets (`edit:gis`, `edit:dax`).
- `platform_core/access/grant.py:136`, `dev_seed.py:57,100` — default module `sbis`.

The composition root `platform-web/src/platform_web/` is where the coupling concentrates. It
imports module code in eight files:

| File | What it hard-codes |
|---|---|
| `app.py:11-16,44-48` | the five `include_*_routers` calls |
| `worker.py:13-33,45-97` | every module's manifest, tasks, hooks, cron |
| `registry.py:47-114` | the launcher catalog: key, label, blurb, home URL, status, `record_noun`, and the two access-only keys (`pmfee`, `pmfin`) — a second copy of what each manifest says (`display_name`, `description`) |
| `admin/modules.py:17-23` | the five manifests, for the directory |
| `wiring/registry.py:22-25,49-61` | four manifests; `LEGACY_WEB_MAP_MODULE = "sbis"`; a `(module, WEB_MAP_SLOT)→page` table |
| `stored_settings.py:31-59` | each module's Setting model and key list |
| `admin/sync_history_tables.py:41-50` | TIVS and CVS sync-run/gap/segment models, to render history |
| `project_map.py:195-246` | TIVS track-span code (`tivs.display`, `tivs.track_span`), gated by `"tivs" in enabled` |
| `readiness.py:74` | `pm.phase.phase_for` directly (skipping the PM seam adapter) |
| `data.py:834-835` | literal links `/tivs/sync`, `/cvs/sync` |

Two more asymmetries: the core exposes **no** "module X is enabled for this project" check to
plugins except `DbAccessService.enabled_modules` (used by `sbis/web/routes.py:1362`), and the
launcher lists only `status="available"` modules, so absent modules are already invisible there.

### 2.4 Shared GIS data as an implicit seam

- `track_centerline` is one dataset that CIV binds as a non-marker slot (`civ/manifest.py:176`,
  `civ/assets.py:245`), TIVS declares as a source (`tivs/assets/track.py:23`), and the shell draws
  (`project_map.py:87`). Three consumers, no owner; it lands once because `lands_by_objectid` says the
  dataset only relaxes the GlobalID rule if **every** consumer opts in (`datasets.py:83-93`).
- SBIS, CIV and TIVS declare slots on the same physical datasets (`signals`, `crossings`, `turnouts`,
  `diamonds`, `derails`, `wayside_detectors`, `generators`; `civ/manifest.py:_DATASET_BY_KEY`). Dataset
  identity is a string agreed by convention. CIV's `bungalow` slot maps to dataset `bungalows`
  (the one key whose name differs).
- The GIS sync already gives a real inter-module event: dataset landed → each consumer's hook runs.
  That is the platform's one working "plugin reacts to another's data" mechanism, and it isolates
  failures per hook (#879).
- Alternatives: `alternative_slot_groups` (TIVS turnout/wayside era pairs) is the only place a
  manifest says "these bindings are mutually exclusive".

## 3. What is wired by hand today (the "add a module" checklist)

To add a module the current code needs edits in: `platform_web/app.py`, `worker.py`,
`registry.py`, `admin/modules.py`, `wiring/registry.py` (if it has a map slot), `stored_settings.py`,
`platform_core/web/chrome.py` (colour), `platform_core/access` (if it has new facets or keys),
`deploy/migrate_remote.sh` (glob; ok), `pyproject.toml` (workspace), plus one `composition.py` and
one `manifest.py` inside the module. The MISSION contract replaces all of the outside edits with
one declaration.

## 4. What each module offers and consumes (for the contract)

Legend — **offers**: things other modules or the shell use. **consumes**: what it needs from the
core or other modules. "Missing-module behaviour" is what should happen when the other side is absent.

### SBIS (`modules/sbis`, schema `sbis`, 53 migrations; 51 when first written)
- **Routes:** ~33 routers under `/sbis`, plus `/api/v1/sbis` (PAT). Literal-before-parameter mount order matters. Biggest file `web/routes.py` 2,833 lines (#842).
- **Models:** bungalow, signal asset and asset fields, catalog, costs, units/main systems/templates, external refs, `SbisSetting`, RR-audit import tables (#1997).
- **Migrations:** own chain; ~10 data migrations read `platform.*` (GlobalID backfill, project FKs).
- **Permissions:** module key `sbis`; facets `edit:inventory`, `edit:costs`, `edit:gis`, `edit:dax`; project-admin settings.
- **Nav / config surfaces:** one nav item in the manifest (`Bungalows`), config surfaces for settings, catalog, templates. A second nav entry, `/sbis/rr-audit` ("RR Audit"), is declared in `web/layout.py:248` (`_NAV_SECTIONS`) and **not** in `SBIS_MANIFEST`: nav declared outside the manifest (added v1.60.0). RR-audit routes number 23 handlers in `web/rr_audit_*.py`, admin tier; `composition.py` has 36 `include_router` calls (30 at v1.59.1).
- **Data classes (ADR 0025):** the RR-audit tables are *third-party evidence held beside the inventory*, a class ADR 0016 §3 now names. `catalog_delete`/`catalog_merge` carry a `crosswalk` blocker (RESTRICT reference to the catalog): the first case of another table family pointing into the catalog.
- **Jobs:** `sbis_generate_inventory_sheets`, `sbis_parse_rr_audit`; sync hooks (bungalow halves; per-family include mirroring).
- **Offers (links/data):** bungalow/asset detail pages (`/sbis/bungalows/by-gis/{id}`); `sbis:contents` card slot; the priced-inventory DTOs TIVS consumes (`sbis.seam`, `asset_seam`, `estimate`); validation provider; conversation anchors `bungalow`, `asset`, `catalog_item`; PAT API.
- **Consumes:** GIS datasets `bungalows` (required) and nine asset families; PM phase; CIV 360° card (host route + import); TIVS asset URL (by shape).
- **Missing-module behaviour today:** TIVS link hidden unless TIVS enabled *and* granted (`routes.py:1355-1369`); CIV card imports fail at import time if CIV is absent.

### CIV (`modules/civ`, schema `civ`, 4 migrations)
- **Routes:** viewer, bookmarks, bookmark manager, settings, search, markers, frames, static JS; the *card* routes live in SBIS/TIVS.
- **Models:** `CivBookmark`, `CivFrameMetadata`, `CivAssetMarker`, `CivSetting`.
- **Permissions:** module key `civ`; a TIVS user without CIV still gets the card (deliberate).
- **Nav:** `Viewer`, `Bookmarks`.
- **Jobs:** none.
- **Offers:** `civ:pano` card slot; `resolve_asset_pano(...)`; viewer deep link; asset search and markers over other modules' datasets.
- **Consumes:** `oid` dataset (required, OBJECTID identity declared); ten asset datasets; `track_centerline`; detail URLs of SBIS and TIVS (`assets.py:43,76`); tiles from S3 via a resolver (`rmi-imagery-tiling`).
- **Missing-module behaviour:** marker click-through URLs are baked in, so with SBIS or TIVS absent they 404.

### TIVS (`modules/tivs`, schema `tivs`, 48 migrations)
- **Routes:** ~35 routers under `/tivs`, `/api/v1/tivs`; five-stage run pipeline.
- **Models:** inventory/costing/RCN/depreciation/valuation runs and assets, `asset_cost`, `TivsSetting`, snapshots (`TivsValSnapshot`), sync run/gap.
- **Permissions:** module key `tivs`; facets `edit:costs`, `edit:rates`, `edit:valuation`.
- **Nav / config surfaces:** many (cost layer, depreciation, obsolescence, scope, display, columns).
- **Jobs:** `tivs_sync_inventory`, `tivs_generate_costs`, `tivs_run_rcn`, `tivs_take_snapshot`, `tivs_generate_sheets`; sync hook per typed source.
- **Offers:** asset pages (`/tivs/asset/{process}/{id}`, `/tivs/map/asset/{slot}/{id}`); validation provider; anchor `asset`; valuation snapshots; track span lines for the shell map.
- **Consumes:** SBIS priced inventory (via seam), PM phase, CIV card, track and 15+ inventory datasets with era pairs; `platform_core.provenance`.
- **Missing-module behaviour:** SBIS absent → the seam import fails, so **TIVS cannot start** without SBIS (the ADR 0010 rule makes SBIS the bungalow source of record, but signals, crossings and turnouts do not need it).

### CVS (`modules/cvs`, schema `cvs`, 5 migrations)
Not in MISSION.md's module list, but built and mounted. Routes `/cvs/valuation`, `/cvs/reference`,
exports; `/api/v1/cvs`; models valuation run/subject, sales groups, unit values, `CvsSetting`, sync
run/gap, `SubjectSegment`; a published-view API (`/api/v1/cvs/views/<view>`, `?section=`, revision token, snapshot-read pager) and packaged Power Query files served at `/cvs/connect/powerquery/<name>.pq` (v1.62.1–2); task `cvs_sync_subject_segments`; hook `register_cvs_sync_hooks`; consumes
one dataset and the PM phase. Offers no links. It is the cleanest plugin today and is the natural
test of the contract. **Question for the operator (goes in the proposal):** is CVS in scope for the
rebuild?

### PM (`modules/pm`, schema `pm`, 8 migrations)
- **Routes:** `/pm` workspace, properties, fees, parties surface, finance; QBO under core.
- **Models:** `Property` (scope: `asset_categories`, `subdivisions`, one per project), `Document`, `ProjectPhase`, fee rule/structure/estimate snapshot.
- **Permissions:** keys `pm` (cannot be disabled, always on) plus **access-only** keys `pmfee`, `pmfin` that carry no page — the contract needs "a key that is a permission, not a place" as a first-class thing.
- **Jobs:** `pm_sync_qbo` daily cron (`RMI_QBO_SYNC_HOUR_UTC`; negative disables).
- **Offers:** `phase_for` (SEAM_VERSION 1), used by three modules and by the readiness page; project phase feeds the shared validation engine.
- **Consumes:** parties, sections (core), QBO (core). Property scope is *stored* in PM but no module reads it through a seam today (grep finds no consumer); the 0.1 inventory's "SBIS reads property scope" is not supported by the code.
- **Owns something the core reads:** `platform_core.sections` (project sections) is core-owned with PM as steward.

## 5. Planned, not built: what each needs from the contract (issues §1, §4)

| Planned item (issue) | Contract need |
|---|---|
| GIS write-back queue (#866, #1220-1225) | Core service, but **each module declares which of its fields may be written back** (allowlist, per dataset/field), the capability `gis.write_back` exists in core, the pending-change overlay must be applied by whoever reads synced rows (a read hook, not a per-module rewrite), approval per field, rollback by inverse change. Plugin → core: `writable_fields`. Core → plugin: overlay wrapper on the synced-row reader. |
| Third-party evidence lands beside, never in, the inventory (ADR 0025, #1997 waves #2000-2004; issues §4 #14) | A plugin that consumes another plugin's identity (`bungalow`) and offers a comparison result; it needs "link to bungalow" without importing SBIS. Natural first *pure consumer* plugin. |
| Cross-module deep links (#435) | A shared link registry (§6.2). Today's three hard-coded URL schemes are exactly what #435 named. |
| Unlink, the fourth ADR 0023 operation (#1950) | A link **lifecycle** (create/relink/unlink/audit), not only a link *read*. Bungalow↔GIS feature is a link SBIS owns and the shell shows. |
| Embeddable 360 card, admin pinned view (#875 → #1232/#1233) | Card-slot contract exists (`web/slots.py`); needs the host-independent card (no CIV import in host) and `surface` (`page`/`panel`) already in `SlotContext`. |
| CIV conversation anchor (#1439) | Anchor identity for a frame (OBJECTID vs GlobalID; open owner question). Contract needs anchors keyed on a declared identity kind. |
| Provenance across the SBIS→TIVS seam (#1434) | Offered data types carry `(source, as_of, completeness)`; consumer copies them into its snapshot. |
| Restricted client login, CIV-only mode (#261, #437, #1981) | Permissions declared per module as *capabilities*, and a principal type that is not a Portal user. Nav and cards must filter by the caller's grants (they do for links today, by hand). |
| Archive/capsule (#455, #1423) | Optional `export_capsule(project) -> files + manifest` per module; each module's tables must be enumerable from its declaration. |
| Fee estimator rework (#1829, MISSION) | Configuration with overrides and justification is a module-internal concern, but *settings with provenance* is common to SBIS costs, TIVS cost layer and PM fees; a core "override with reason" primitive would remove three private copies. |
| Documents, valuation year, BSIVS, strip maps (tabled or undecided) | Nothing: do not design for them. |

## 6. What the plugin contract has to carry

Derived from §2-§5. Each line says what to declare, and where today's code shows the need.

### 6.1 One declaration, no outside edits
A module ships **one manifest** (typed, machine-readable, validated at load) from which the core
derives everything §3 lists by hand: routers (with mount order or a "literal paths first" rule the
core applies), GIS datasets and slots, sync hooks, validation provider, anchors and resolvers,
card slots, worker tasks and cron (with a schedule setting and an off switch), settings keys, access
keys and facets, nav, config surfaces, launcher metadata (label, blurb, record noun, colour),
migration chain location and schema, static assets, PAT API prefix. Both the API and the worker read the
same manifest, removing the "register in both roots or the hook silently never fires" trap
(`sbis/composition.py:register_sbis_sync_hooks` docstring).

### 6.2 Links offered and consumed
- **Offered:** a named *link target kind* with an identity type (`bungalow`:GlobalID, `signal_asset`:GlobalID,
  `tivs_asset`:(process, asset_id), `oid_frame`:OBJECTID), a URL builder or route template, the
  permission needed to open it, and a label. Replaces `tivs_asset_url`, `sbis_lines.py:172`,
  `civ/assets.py:43,76`, `viewer_url`.
- **Consumed:** a module names the target *kind* and gets back either a link or nothing. The core answers
  "does a provider exist, is it enabled on this project, may this caller open it" in one place
  (today each producer re-derives it: `routes.py:1355`, `pano_card.viewer_link`).
- **Bidirectional mapping** between kinds: bungalow → its panoramas, its TIVS assets, its conversation thread.
  Expressible as `(from_kind, to_kind, resolver)` so an SBIS bungalow finds CIV panoramas without either importing the other.
- **Absent provider = no link and no gap**, by construction.
- **Card slots** (already in core) are the second kind of link: a host page shows a foreign card.
  Keep `<module>:<card>` naming, healing render, SAVEPOINT, and add a declared identity kind the card accepts.

### 6.3 Typed data seams (not only links)
For data other modules read (SBIS priced inventory → TIVS, PM phase → three modules): a **versioned,
typed, declared interface** with the offering module owning identity and normalisation (#1054), carrying
provenance (#1434), and a machine-readable schema. The consumer declares the interface and version it
expects; the core fails start-up (as today's version assert does) or disables the consumer with a
named reason. Optional vs required: TIVS needs SBIS **only for bungalows and SBIS-priced families**,
so the dependency should be per-feature (`requires` vs `uses_if_present`), not per-module.

### 6.4 Models and migrations
Schema per module and an own Alembic chain both work (six chains, drift-checked by
`scripts/alembic_drift.py`); keep them. Add: a declared dependency on the **core migration revision**
it needs (today ordering is by convention and by `deploy/migrate_remote.sh`), a rule that cross-schema
reads in migrations name the core table by a stable core API, and no module→module migration
dependency. `project_id` stays an unconstrained UUID in module tables (ADR 0002).

### 6.5 Permissions
Module key with role + editor facets as today, plus: **access-only keys** (`pmfee`, `pmfin`), facets declared by the
module rather than a core enum (SBIS's `edit:gis`/`edit:dax` do not belong to the core),
capabilities declared by the module (`gis.write_back` for write-back), and "always on" (PM). A link's
required permission comes from the target's declaration.

### 6.6 Navigation and shell
Nav items, config surfaces (already with `requirement` tiers and `visible_to`) and launcher card come from
the manifest. Keep four-bar layout (ADR 0020). Remove the second launcher catalog in
`platform_web/registry.py` and the accent-colour table in `chrome.py`.

### 6.7 Jobs and events
Task functions and cron schedules declared in the manifest, wrapped by the core in metrics. One event
that exists today and should be first-class: **dataset landed** (project, dataset, run id) → hooks, each isolated, each
result recorded on the run (`hook_results`). Add likely-needed events: *project phase changed*,
*link created/removed* (for #1950 and audit), *snapshot sealed*. The queue boundary (`enqueue`) already lets the
broker change.

### 6.8 GIS
Slot→dataset declaration exists and is right. Add: dataset **identity kind** (GlobalID, or OBJECTID for
the OID layers: `objectid_identity`), `alternative_slot_groups`, the per-field write-back allowlist, and
a **shared-dataset ownership rule** so `track_centerline` has a declared owner and the others are readers.
Sync-run freshness must be readable by any consumer ("latest run failed" vs "no rows"), so that
"absent / undecided / excluded / failed" stay distinct (issues §3.2).

### 6.9 Settings, config, audit, validation, conversations
Already contract-shaped and worth keeping as they are: `SettingKey` + `ConfigSurface`, `DbAuditSink`
(transactional), validation provider `(session, project, phase) -> ModuleReport`, conversation anchors +
resolvers. Change only the registration path (via manifest) and give settings a core override-with-reason primitive.

### 6.10 LLM/tool legibility
Everything in 6.1-6.9 being one typed manifest makes "what does this platform have?" a single
query: modules, routes, link kinds offered/consumed, datasets, permissions, jobs, decisions (with
ruled/tabled/open status; issues §4 #13). Today an agent must read `composition.py` in every module and
eight shell files.

## 7. Risks and open points for the proposal

1. **CIV code in SBIS/TIVS** is the hardest seam to cut: the card fragments, controller JS and CSS are shared
   strings. Choose one: the card is a core kit widget fed by a CIV *service*, or it is a card slot with no host imports.
2. **TIVS→SBIS mandatory import** blocks any TIVS-without-SBIS deployment; decide per feature (§6.3).
3. **Route-order coupling** (literal before parameter) is a hidden contract; the core should sort or reject ambiguity.
4. **Two composition roots** (API, worker) each hand-register hooks; one manifest read removes the class of bug.
5. **Not checked:** runtime behaviour of any seam, test coverage of link visibility, whether the CVS pm_seam is used beyond the phase, the contents of `sbis.seam` DTO fields beyond names, and the tools under `tools/rmi-mcp`. Import counts are line counts, so a multi-name import counts once per line.
6. **Question for the operator:** CVS in scope? Is the standalone CIV viewer (#1981) a plugin or a separate deployable?
