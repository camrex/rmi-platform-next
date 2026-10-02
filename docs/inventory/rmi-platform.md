# RMI Platform Inventory

**Repository**: `~/sources/rmi-platform`  
**Status**: Live in production at `apps.rmigis.cloud` — version 1.62.2 (as of 2026-09-30)  
**Corrected 2026-10-02 (task 0.7b)**: written against v1.59.1; version, ADR range, Alembic summary, SBIS (RR Audit) and CVS (Power Query) updated. See `changes-since-2026-09-30.md`.  
**Tech stack**: Python 3.12, FastAPI, PostgreSQL (schema-per-module), Redis (ARQ worker), HTMX + server-rendered HTML (htpy), ArcGIS Enterprise Portal OAuth  
**Deployment**: AWS Lightsail container, one image (api/worker dual entrypoint), Docker Compose locally

---

## Overview

**RMI Platform** is a modular monolith: one FastAPI application, one PostgreSQL database, one deployable container. Five live modules (SBIS, CIV, TIVS 2.0, CVS 2.0, PM) register with a shared core, each with its own schema and Alembic migration chain. Navigation is project-first (every module URL carries `?project=<code>`). GIS integration is read-only today: one-way sync from ArcGIS Enterprise Portal feature services into platform-owned tables.

---

## Directory Layout

```
platform/                  # Platform core (identity, access, projects, GIS, audit, storage, worker, documents)
  ├─ src/platform_core/    # Frontend-agnostic services
  ├─ alembic/              # Platform schema migrations
  ├─ tests/                # Platform tests
  └─ Dockerfile            # Single image: `docker compose build` or `uvicorn platform_web.app:app` for dev
platform-web/              # Composition root (landing, admin, project home, module assembly)
  ├─ src/platform_web/     # Shell: home picker, project workspace, /admin, /p/{code}
  └─ tests/
modules/
  ├─ sbis/                 # Signal Bungalow Inventory System (reference module)
  ├─ civ/                  # Corridor Imagery Viewer (360° panoramas)
  ├─ tivs/                 # Track Inventory & Valuation System 2.0
  ├─ cvs/                  # Corridor Valuation System 2.0 (land valuation)
  └─ pm/                   # Project Management (party registry, lifecycle, fee estimation)
deploy/
  ├─ lightsail-deployment.json  # Infrastructure manifest
  ├─ preflight.sh, smoke.sh     # Deployment validation
  └─ db_backup.sh, db_restore.sh
scripts/                   # Operational helpers (alembic_drift.py, roadmap.py, standup.py, etc.)
docs/
  ├─ adr/                  # Architecture Decision Records (0001–0025): settled decisions
  ├─ planning/             # Roadmap, release notes, owner rulings
  └─ DEPLOYMENT.md         # Deployment procedures
tools/
  └─ rmi-mcp/              # MCP server: read-only analytical API over PAT (not a platform surface)
.env.example               # Full environment variable contract
conftest.py               # Pytest fixtures (workspace-level, shared across modules)
docker-compose.yml        # Local dev stack: Postgres 18, Redis 7, API, worker
pyproject.toml            # uv workspace + all dependencies
.python-version           # 3.12 (pinned)
rmi-platform.code-workspace   # VS Code multi-folder layout
```

---

## Platform Core (`platform/src/platform_core/`)

**DB Schema**: `platform` (Alembic chain: `platform/alembic/versions/`)

### Services

| Module | Role | Key files |
|--------|------|-----------|
| **identity** | ArcGIS Portal SSO (OAuth2 code flow); signed session cookie; dev-identity fallback | `identity/` — `sso.py`, `session.py` |
| **access** | RBAC: (user, project, module) → role + permissions; every route depends on `require_module_access("<key>")` | `access/` — queries return `AccessContext` |
| **projects** | Business context: client, railroad, region, logos; per-project module enablement; project-scoped settings | `projects/` — `models.py` (Project, ProjectModule, ProjectGisDataset) |
| **parties** | Organization + contact registry; project-scoped role bindings (ADR 0014); PM module surfaces this | `parties/` — contacts, orgs, roles; PM owns the UI |
| **GIS** | Read-only sync from ArcGIS Portal; dataset catalog; feature-service bindings per project; attribute-level synced rows | `arcgis/` — see below |
| **audit** | Transactional audit trail: every record change rides `DbAuditSink.record(AuditEvent)` in the same transaction | `audit/` — `db.py` (AuditEvent, DbAuditSink); change can't land if audit fails |
| **storage** | S3 (prod) / local disk (dev) abstraction; scoped key paths; access-checked streaming | `storage/` — one backend protocol |
| **tokens** | Personal Access Tokens (PATs): plaintext shown once, SHA-256 at rest, expiring, revocable, user-scoped | `tokens/` — `models.py` (PersonalAccessToken); `/api/v1/tokens` endpoint |
| **worker** | ARQ on Redis: background jobs; scheduling; GIS sync runner; backup jobs | `worker/` — `queue.py` (enqueue), `tasks.py` (ping, sync_gis_datasets, scheduled_gis_resync, scheduled_db_backup) |
| **documents** | HTML→PDF: WeasyPrint over htpy print templates; platform-owned service; base chrome, provenance stamp (version + git SHA) | `documents/` — print templates + PDF generation |
| **validation** | Shared validation engine (ADR 0024): modules register rules; platform evaluates against project phase; result per (user, project, asset, rule) | `validation/` — rules engine; SBIS registers bungalow checks; TIVS registers asset checks |
| **conversations** | Platform-owned threading layer (ADR 0019); modules declare anchors (bungalow, asset, catalog_item); threads attach to entity detail pages | `conversations/` — types, resolvers, moderation |
| **api** | Frontend-agnostic API: `/api/v1/tokens`, `/api/v1/analytics/whoami` (PAT resolution); analytical data access | `api/` — routers for PAT endpoints |
| **web** | Shared HTML kit (ADR 0020): `platform_core.web.shell` (document chrome, layout, nav bars, tokens), icons, vocabularies (tag, status_line, field_error, banner), tabs, card slots, refusals | `web/` — `shell.py`, `layout.py`, `icons.py`, `tokens.py`, `vocab.py` |
| **sections** | Content areas under project home; modules register sections | `sections/` — registry for `/p/{code}` areas |
| **observability** | Metrics (Prometheus), logging (correlation context), health | `observability/` — `metrics.py` (golden-signal middleware) |
| **qbo** | QuickBooks Online integration (ADR 0014, PM wave 1) | `qbo/` — OAuth, entity landing |
| **registry** | Module manifest types: `ModuleManifest`, `GisSlot`, `NavContribution`, `ConfigSurface`, `ConversationAnchor` | `registry/` — where modules declare themselves |
| **testing** | Pytest fixtures: session DB, access context, etc. | `testing/` — reused by all modules |
| **db** | SQLAlchemy setup: `DeclarativeBase` with `NAMING_CONVENTION` (stable constraint names), session factory | `db/` — `base.py`, `session.py` |

### Key Architecture Patterns

1. **Cross-schema design** (ADR 0002): One PostgreSQL database, one schema per module. Modules never ORM-join across schemas — they reach platform data through services.
2. **Transactional audit** (ADR ???): `DbAuditSink.record(AuditEvent)` rides the caller's transaction. An unauditable change cannot land.
3. **No circular imports**: `platform_core` exposes services; modules import from `platform_core`, never the reverse.

---

## GIS Integration (`platform/src/platform_core/arcgis/`)

**Read-only, attribute-level sync; maps stay client-side (ADR 0016); one-way Portal→platform.**

| File | Purpose |
|------|---------|
| `catalog.py` | ArcGIS Portal item catalog (web maps, feature services, tables) indexed per project; `ProjectGisDataset` binding (ADR 0016) |
| `contracts.py` | `SourceContract`: what a module needs (layer name, field list, ID field, geometry expectation) |
| `sources.py` | Per-asset `SourceCode`: which dataset → which Alembic landing table |
| `datasets.py` | Per-project dataset binding (`GisDatasetBinding`): layer URL, refresh schedule; resolved at sync time |
| `synced.py` | **Attribute sync**: `sync_dataset()` fetches full layer → validates against contract → lands JSONB verbatim + decoded labels by object ID; `GisDatasetSyncRun` + `GisDatasetSyncGap` tables track runs |
| `synced_sequence.py` | Utility: walk synced rows by OBJECTID; used by modules for attribute reads |
| `landing.py` | Core landing logic: `SourceContract` → `LandingPlan` (which fields to land, computed calc fields); row landing with coded-value decoding |
| `request_sync.py` | Enqueue a sync for a dataset: `SyncRequest` → worker processes it |
| `sync_control.py` | Refusal logic: old-value mismatch, moved geometry → mark sync as refused, audited; applied only if old value still matches (deferred change queue contract, MISSION.md) |
| `sync_history.py` | Read sync run history per (project, dataset); reports success/failure/gaps |
| `sync_hold.py` | `GisSyncHold`: pause syncing a dataset during admin work |
| `client.py` | Low-level Portal feature-service client (list layers, query) |
| `token.py` | Portal OAuth token refresh (one-time, app-owned credential) |
| `browser_token.py` | Minted app-scoped token for maps in the browser (referer-bound, ADR 0015) |
| `export.py` | Server-side raster export for PDFs (the one exception to client-side maps, ADR 0016 amendment 2026-09-11) |
| `project_map.py` | Framed web-map export for project home, cached per project |
| `health.py` | GIS reachability probe (worker task) |
| `errors.py` | ArcGISError, ArcGISRequestError, ArcGISConfigError → HTTP error responses (503/409 via `http_errors`) |
| `discovery.py` | Portal item discovery utilities |
| `field_grammar.py` | Field name validation, aliases |
| `layer_identity.py` | Stable layer references across Portal updates (by name, layer index) |
| `grant_state.py` | Track what read permissions exist on a dataset |
| `probe.py`, `gis_probe.py` | Health checks (scheduled task in worker) |

**Sync Workflow**:
1. Admin binds a feature service layer at `/p/{code}/data#wiring` (maps `GisSlot` to `GisDatasetBinding`)
2. Route or cron enqueues `sync_gis_datasets` (worker task)
3. Worker fetches full attribute map from layer via Portal client
4. Validates against declared `SourceContract` (fields, types, ID)
5. Lands as platform-owned `gis_dataset_synced_<dataset>` table: JSONB verbatim + decoded labels by object ID
6. If old-value check fails, records refusal (deferred change queue contract)
7. Modules read from synced table (`synced_sequence.rows_near()`) instead of hitting Portal again

---

## Modules

### SBIS: Signal Bungalow Inventory System

**Path**: `modules/sbis/src/sbis/`  
**DB Schema**: `sbis` (Alembic: `modules/sbis/alembic/versions/`)  
**Manifest**: `manifest.py` → `SBIS_MANIFEST`  
**Routes Assembly**: `composition.py` → `include_sbis_routers(app)`

**Purpose**: GIS-integrated inventory of signal bungalows and equipment; single source of record for TIVS/CVS bungalow list (ADR 0010).

**Models** (`models.py`):
- `Bungalow`: main record, links to GIS feature by GlobalID, equipment counts roll-up, cross-chassis chassis type
- `Asset` (signal asset) + `AssetField` (equipment): typed, costed
- `MainSystem` (group of units), `Unit` (platform/category/subsystem combo)
- `CatalogItem`: equipment library (materials, labor, cost)
- `Cost`: project price list per item
- Equipment, batteries, generators, detectors, crossings, etc. (asset families)
- **RR Audit** (added v1.60.0, #1997; ADR 0025): UP's Signal Asset Audit held *beside* the inventory as third-party evidence, never written into it. Models in `rr_audit/models.py`, `crosswalk_models.py`, `pairing_models.py`: `RrAuditImport`, `Cabin`, `Chassis`, `Module`, `Family` (+`FamilyModel`, `FamilyItem`, `CoverageOverride`), `Pairing`, `Disposition`, `Decision`. `FamilyItem.equipment_catalog_id` is a RESTRICT reference, so catalog delete/merge gained a `crosswalk` blocker.

**Key Routes** (`web/`):
- `/sbis/bungalows` — list + detail/edit; map view
- `/sbis/catalog` — equipment admin
- `/sbis/costs` — project price list
- `/sbis/main-systems` — unit review, templates
- `/sbis/reconcile` — GIS vs. inventory comparison (read-only, identifies unsynced changes)
- `/sbis/summary` — project dashboard (count roll-ups)
- `/sbis/export` — xlsx + Power Query templates
- `/sbis/rr-audit` — Imports, cabins, crosswalk, pairing, comparison, decisions (`web/rr_audit_*.py`, admin tier; nav entry is in `web/layout.py`, not the manifest)
- `/sbis/settings` — display order, naming, GIS field mapping

**Background Jobs** (`composition.py` → `register_sbis_sync_hooks()`):
- `BUNGALOW_SYNC_HALVES`: two audit-isolated adoption hooks after GIS sync (#879)
- `ASSET_INCLUDE_HOOKS`: per-asset-family adoption (turnouts, crossings, etc.) mirrors include flags after their dataset syncs (#901)
- Worker task `sbis_parse_rr_audit` (parses an uploaded audit workbook; registered in `platform-web/.../worker.py`)

**GIS Slots** (manifests signals, crossings, turnouts, diamonds, derails, generators, crossing_structures, wayside_detectors, wayside_detector_equipment):
- `bungalow` (required, project dataset): points with bungalow inventory
- Asset-family slots (optional): nearby picker for related assets

**Seams** (coupling to other modules):
- **TIVS**: SBIS bungalow → TIVS valuation asset link; SBIS reconcile reads TIVS inventory asset counts
- **CIV**: SBIS asset detail includes 360° pano card (embedded viewer)
- **PM**: SBIS reads engagement lifecycle data for property scope

**Test coverage**: `modules/sbis/tests/` — export, reconciliation, asset relations, detector adoption, validation

---

### CIV: Corridor Imagery Viewer

**Path**: `modules/civ/src/civ/`  
**DB Schema**: `civ` (Alembic: `modules/civ/alembic/versions/`)  
**Manifest**: `manifest.py` → `CIV_MANIFEST`  
**Routes Assembly**: `composition.py` → `include_civ_routers(app)`

**Purpose**: Street View-style 360° panoramic viewer over tiled derivatives; frame navigation with map dock; asset-marker overlay.

**Models** (`models.py`):
- `CivBookmark`: user-saved frames (position, pan/tilt/zoom, optional folder)
- `CivFrameMetadata`: cached camera metadata (reel, frame sequence)
- `CivAssetMarker`: asset overlay on frames
- `CivSettings`: per-project viewer config (resolver strategy, preload, initial frame)

**Key Routes** (`web/`):
- `/civ/viewer` — panorama viewer (Photo Sphere Viewer + ArcGIS SDK, islands)
- `/civ/bookmarks/manage` — bookmark list/edit
- `/civ/settings` — imagery resolver, viewer, asset markers, Survey123 form bindings

**GIS Slots**:
- `oid` (required, project dataset): Oriented Imagery Dataset points (camera metadata)
- Asset markers (`signals`, `crossings`, `turnouts`, `diamonds`, `derails`, `wayside_detectors`, `generators`, `lubricators`, `tanks`, `slide_fences`): bindable per-project for overlay
- `track_centerline` (bindable, drawn by TIVS if bound): not a marker

**Architecture** (`pano.py`, `frames.py`, `assets.py`):
- Frame retrieval: OID dataset synced rows → cache metadata
- Tiles: per-project resolver strategy (S3, HTTP) → derivatives pipeline
- Asset markers: renders from synced layer attributes

**Seams**:
- **SBIS**: asset detail includes embedded 360° card; asset search via nearby GIS features
- **TIVS**: draws track centerline if OID bound

**Tests**: `modules/civ/tests/` — frame queries, bookmark CRUD, marker rendering

---

### TIVS 2.0: Track Inventory & Valuation System

**Path**: `modules/tivs/src/tivs/`  
**DB Schema**: `tivs` (Alembic: `modules/tivs/alembic/versions/`)  
**Manifest**: `manifest.py` → `TIVS_MANIFEST`  
**Routes Assembly**: `composition.py` → `include_tivs_routers(app)`

**Purpose**: Five-stage cost-approach valuation pipeline — inventory → costing → RCN → depreciation → valuation — from GIS inventory frames, with parity proof against legacy CTVS golden datasets (ADR 0009, plan `docs/planning/TIVS_2_0_PLAN.md`).

**Models** (`models.py`):
- `InventoryRun`, `InventoryAsset`: GIS-sourced frame snapshot with asset list
- `CostingRun`, `CostingAsset`: apply price book to inventory
- `RcnRun`, `RcnAsset`: residual component net replacement
- `DepreciationRun`, `DepreciationAsset`: age/condition curves
- `ValuationRun`, `ValuationAsset`: final value + exhibits
- `ProcessKey` enum: asset type (structure, rail_bond, crossing, etc.)
- `DayRates`, `CostBook`: reference data

**Asset Registry** (`assets/registry.py`):
- `SourceContract`: inventory source (dataset, fields, how to ID a feature)
- Per-process `AssetSource` (declares which layers + which contract per era)
- Turnout era-pair (Schema-1 vs. Schema-2) + wayside detector era-pair handled with `alternative_slot_groups()`

**Key Routes** (`web/`):
- `/tivs/dashboard` — project inventory roll-up, run readiness
- `/tivs/inventory` — per-run asset list + detail
- `/tivs/costing` — cost runs + grid
- `/tivs/rcn` — RCN runs
- `/tivs/depreciation` — curve application
- `/tivs/valuation` — final surfaces, PDF exhibits
- `/tivs/settings` — cost book management, reference data

**Calculation Logic** (ADR 0009 — code-owned, not config):
- `valuation/` — depreciation curves (Iowa curves, condition curves)
- `inventory/` — asset sourcing from GIS layers + structures
- `costing/` — price lookup logic
- `parity/` — proof against CTVS golden (phase 1 of work, parity era over with #419/#598)

**Background Jobs**: None explicit; costing/RCN/depreciation/valuation are user-triggered runs (readiness gates at each stage, ADR 0024).

**GIS Slots** (turnouttypes, wayside detectors, bungalows, rail bonds, etc. — era-specific):
- Mandatory slots per asset (e.g., `turnout_pt_a` or `turnout_pt_b` depending on schema era)
- One schema binding per project (enforced at `/admin/gis`)

**Seams**:
- **SBIS**: reads bungalow source of record; asset detail card links back to SBIS
- **CVS**: both work from same GIS corridor inventory

**Tests** (`modules/tivs/tests/`): costing logic, RCN calcs, depreciation curves, parity against golden CTVS

---

### CVS 2.0: Corridor Valuation System (Land Valuation)

**Path**: `modules/cvs/src/cvs/`  
**DB Schema**: `cvs` (Alembic: `modules/cvs/alembic/versions/`)  
**Manifest**: `manifest.py` → `CVS_MANIFEST`  
**Routes Assembly**: `composition.py` → `include_cvs_routers(app)`

**Purpose**: Sales-comparison land valuation over GIS-synced corridor subject segments; reference-data grids (unit values, factors); five valuation views with Excel export + Power Query. Parity-proven against frozen 25-320 golden dataset.

**Models** (`models.py`):
- `ValuationRun`, `ValuationSubject`: per-corridor analysis
- `SalesGroup`, `UnitValue`: reference data (unit norm factors, unit values by group)
- `CompariableProperty`: sales in the analysis set
- `ValuationSurface`: final multi-factor results

**Key Routes** (`web/`):
- `/cvs/valuations` — run list + detail
- `/cvs/reference` — unit values, sales groups, factors (admin grid)
- `/cvs/exports` — Excel round-trip: styled export + validated three-mode import
- `/cvs/connect` — Power Query help; serves the packaged `.pq` files (`web/powerquery/`: `fnCvsPaged`, `fnCvsView`, `fnCvsSectionGroups`, `CvsView`, `CvsSectionGroupsView`) at `/cvs/connect/powerquery/<name>.pq` (v1.62.1–v1.62.2, #2020/#2025)
- `/api/v1/cvs/views/<view>` — published views, paged; `?section=1,2,3` applied before the fold; every response carries a `revision` (sync run + reference-table digest + price unit) and pages are read under `session_scope(snapshot=True)`; the `sections` view has no Total row and carries `effective_corridor_factor` and section names. Open: #2023 (revision misses a late commit), #2026 (section groups defined in the platform)

**Calculation Logic** (`valuation/`):
- Unit normalization, two-sided averaging, ATF (adjustment time factor), factor matching
- Parity-proven against the frozen 25-320 golden (owner rules: parity era ended with #419; CTVS legacy sunset is operational work ahead)

**GIS Slots**: Subject corridor segments (named dataset per project).

**Seams**:
- **TIVS**: both consume same GIS corridor inventory (track centerline shared)

**Tests**: `modules/cvs/tests/` — valuation formulas, reference-data grid CRUD, Excel export/import round-trip

---

### PM: Project Management

**Path**: `modules/pm/src/pm/`  
**DB Schema**: `pm` (Alembic: `modules/pm/alembic/versions/`)  
**Manifest**: `manifest.py` → `PM_MANIFEST`  
**Routes Assembly**: `composition.py` → `include_pm_routers(app)`

**Purpose**: Project workspace (ADR 0014): organization/contact registry surfaces (owner in platform-core); engagement lifecycle (stage + key dates); property scope; in-app role management; **Wave 1 shipped**: fee structure, estimate rules, reconcile vs. actual QBO (ADR 0014, owner 2026-08-15). PM also owns the project phase (ADR 0024).

**Models** (`models.py`):
- `PropertyScope`: geographic/asset bounds per project
- Fee structure: `FeeRule`, `FeeStructure`, `FeeSurface` — configurable with overrides + captured justification; effort in days (ADR ??? in MISSION.md)

**Key Routes** (`web/`):
- `/pm/properties` — property scope editor
- `/pm/fees` — fee rule configuration, estimate calculator, approval workflow
- `/pm/parties` (in core, PM surfaces): contacts, organizations, roles

**Background Jobs** (`tasks.py`): QBO sync (fetch budget status, check burn), fee estimate reconciliation.

**Seams**:
- **Core**: reads/writes parties (organizations, contacts, project-scoped roles)
- **SBIS**: reads property scope; asset detail respects property-scoped scope
- **QBO**: OAuth credential binding, budget sync (platform_core.qbo)

**Tests**: `modules/pm/tests/` — fee calc, QBO sync, phase transitions, property scope

---

## Models & Validation

### Shared Model Patterns

**Cross-schema FK rule** (ADR 0002): All modules avoid ORM-joined foreign keys across schemas.
```python
# Example: SBIS Asset.project_id references platform.Project, but no ORM relationship
project_id = Column(Integer)  # No ForeignKey() declaration
# Reach platform data through services instead:
project = await get_project(session, project_id)
```

**Validation** (ADR 0024): Shared engine per project phase; modules register rules.
```python
# SBIS registers bungalow checks via composition.py:
register_validation_provider(MODULE_KEY, sbis_validation_report, sbis_validation_rules)
# Core engine evaluates all rules, stores results per (user, project, asset, rule)
```

**Audit** (transactional): Every write rides `DbAuditSink.record()`.
```python
# Example: equipment delete is auditable only if audit succeeds
await DbAuditSink.record(AuditEvent(...), session)
# Unauditable change cannot land
```

---

## Routes & Navigation

### Route Structure

**Project-first navigation** (ADR 0013): Every module route carries `?project=<code>`.

**Layout hierarchy** (ADR 0020 §navigation):
- **Bar 1** (app-level): Platform home, sign out
- **Bar 2** (project-level): Project name, module picker (registered via `nav` in manifests)
- **Bar 3** (module-level): Module title + section nav (per-module `layout.py` supplies `nav()`)
- **Bar 4** (page-level, optional): Page-specific nav/actions (declared via `PageBar` in `page(page_bar=…)`)

**Module registration** (`manifest.py → nav`):
```python
# SBIS example
nav=[NavContribution(label="Bungalows", path="/sbis/bungalows", icon="home", order=10)]
```

**Landing pages**: `home_router` (platform picker), `project_router` (/p/{code}), module `home_router` (section launcher).

---

## Migrations & Database

### Alembic Chains (Per-Module)

| Module | Chain | Current | Purpose |
|--------|-------|---------|---------|
| platform | `platform/alembic.ini` | `0043_oid_sequence_indexes` (44 files; corrected 2026-10-02, was "0027") | Core tables: user, project, audit, access, parties, GIS catalog, tokens, validation |
| sbis | `modules/sbis/alembic.ini` | `5b7d2e9c4a13` `family_group_key` (53 files; RR Audit added three in v1.60.0) | Bungalows, assets, equipment, catalog, costs |
| civ | `modules/civ/alembic.ini` | Latest | Bookmarks, frame metadata, asset markers, settings |
| tivs | `modules/tivs/alembic.ini` | Latest | Inventory, costing, RCN, depreciation, valuation runs + assets |
| cvs | `modules/cvs/alembic.ini` | Latest | Valuation runs, subjects, sales groups, unit values |
| pm | `modules/pm/alembic.ini` | Latest | Fee structure, estimates, property scope, phase |

**Upgrade all chains**:
```bash
uv run alembic -c platform/alembic.ini upgrade head
uv run alembic -c modules/sbis/alembic.ini upgrade head
uv run alembic -c modules/civ/alembic.ini upgrade head
uv run alembic -c modules/tivs/alembic.ini upgrade head
uv run alembic -c modules/cvs/alembic.ini upgrade head
uv run alembic -c modules/pm/alembic.ini upgrade head
```

**CI gate** (`scripts/alembic_drift.py`): Migrations applied to a scratch DB + `alembic check` on every chain.

### Schema Version Tables

Each chain owns its version table:
- `platform` → `alembic_version` (standard name)
- Other modules → `alembic_version_<module>` (unique per schema)

---

## Background Jobs & Worker

**Implementation**: ARQ on Redis (ADR 0003)

**Worker Entrypoint**: `uvicorn platform_core.app:worker` (same container image, different entry)

**Enqueue Boundary** (`platform_core.worker.queue`):
```python
async def enqueue(function: str, *args, **kwargs) -> str | None:
    # Thin wrapper over ARQ; lets broker swap (e.g., to SQS) without touching callers
```

**Core Jobs** (`platform_core.worker.tasks.py`):
| Job | Schedule | Purpose |
|-----|----------|---------|
| `ping` | Manual | Health check |
| `sync_gis_datasets` | Manual or cron | Fetch & land GIS attributes (platform_core.arcgis.synced) |
| `scheduled_gis_resync` | Cron (configurable) | Periodic re-sync of all enabled datasets per project |
| `scheduled_db_backup` | Cron (configurable, prod only) | PG dump to S3 |
| `probe_gis_reachability` | Cron | GIS health check |

**Module Jobs**:
- **SBIS**: adoption hooks after bungalow sync (`register_sbis_sync_hooks()` in composition)
- **PM**: QBO sync tasks (`tasks.py` → enqueue)

**Job Registration**: Modules call `register_sync_hook(dataset, hook_fn)` in composition (not auto-discovered).

---

## Tests

**Framework**: pytest (Python 3.12)  
**Fixtures**: Workspace-level `conftest.py` + per-module overrides

**Structure**:
- `conftest.py`: session DB, DB URL injection, async test helpers
- `platform/tests/`: core services (audit, access, GIS)
- `modules/*/tests/`: module-specific tests (models, routes, calculations)

**Coverage** (examples):
- SBIS: reconciliation, asset relations, detector adoption, export, validation
- TIVS: costing calcs, RCN, depreciation curves, parity vs. golden CTVS
- CVS: valuation formulas, Excel round-trip
- PM: fee calculations, QBO sync, phase transitions
- CIV: frame queries, bookmarks
- Platform: GIS sync, audit, access control

**CI Gate**:
```bash
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run pytest
uv run python scripts/alembic_drift.py
```

---

## Deployment

**Target**: AWS Lightsail container (prod: `apps.rmigis.cloud`, version pinned by release tag)  
**Image**: Single Docker image, dual entrypoint (API / worker)  
**Compose**: Local dev via `docker-compose.yml` (Postgres 18, Redis 7, API, worker)

### Deploy Artifacts

| File | Purpose |
|------|---------|
| `platform/Dockerfile` | Single image: Python 3.12, FastAPI, migrations, ARQ worker |
| `deploy/lightsail-deployment.json` | Infrastructure manifest (instance size, secrets, env vars) |
| `deploy/preflight.sh` | Pre-deploy checks (image pulls, schema validation) |
| `deploy/smoke.sh` | Post-deploy checks (health endpoints, sample queries) |
| `deploy/migrate_remote.sh` | Run Alembic chains on remote (via SSH) |
| `deploy/db_backup.sh`, `db_restore.sh` | Backup/restore workflows |
| `scripts/save_image.py` | Image push/tagging |
| `scripts/bump_version.py` | Semantic version increment + changelog |

### Deployment Procedure

1. **Build**: `docker build -t rmi-platform:vX.Y.Z -f platform/Dockerfile .`
2. **Push**: ECR tag + push
3. **Migrate**: SSH to Lightsail, run `deploy/migrate_remote.sh` (all six chains)
4. **Deploy**: Lightsail container service update (new image)
5. **Smoke**: Run `deploy/smoke.sh` (health, sample data)

---

## How Modules Share Code

### Dependency Hierarchy

```
platform_core (identity, access, projects, GIS, audit, storage, worker, documents, validation, conversations)
    ↓ (imported by)
platform_web (shell, landing, admin, project home)
    ↓ (imports)
Every module (sbis, civ, tivs, cvs, pm)
```

### Cross-Module Sharing (No Circular Imports)

1. **Platform-owned services** (parties, validation, conversations, storage, documents, observability): Modules call services, services are singleton per app.
2. **Manifest registry** (`platform_core.registry.ModuleManifest`): Modules declare slots, nav, config surfaces; platform reads them.
3. **Web kit** (`platform_core.web`): Shared HTML components, icons, tokens, vocabularies — modules `import from platform_core.web` and never re-copy (ADR 0020).
4. **GIS dataset** synced rows: Modules call `synced_sequence.rows_near(dataset)` to read attributes (not each hitting Portal).
5. **Audit**: All write to the same `DbAuditEvent` table (platform schema).

### What Modules Do NOT Share

- **Models**: Each module owns its schema; no cross-module table joins in ORM.
- **Routes**: Each module's router is mounted independently in composition root.
- **Jobs**: Each module registers its own hooks; no auto-discovery.

### Example: SBIS + TIVS Seam

**SBIS is bungalow source of record (ADR 0010); TIVS consumes it.**
- SBIS model: `Bungalow(project_id, gis_globalid, name, …)`
- TIVS model: `InventoryAsset(project_id, asset_type, bungalow_id, …)` — foreign key to SBIS only at read time (no ORM FK)
- TIVS code reads bungalows: `from sbis.models import Bungalow; session.query(Bungalow).filter(…)`
- Route: TIVS asset detail card links to `/sbis/bungalows/{bungalow_id}?project={code}`

---

## GIS Integration Summary

**One-way sync, attribute-only** (read-only for now, ADR 0016 + 0023):

1. **Binding** (`/admin/gis`): Admin selects Portal layer → maps to GisSlot → declares include flags (post-sync adoption).
2. **Sync** (worker `sync_gis_datasets` task): Fetch full attribute map from layer → validate against contract → land in `gis_dataset_synced_<dataset>` (JSONB + decoded labels).
3. **Read** (modules): `rows_near()` from synced table instead of calling Portal again.
4. **Write** (deferred change queue): If old-value check fails, mark sync as refused, audited; PM can review/approve later (contract in MISSION.md).

**Modules declare what they need** (`manifest.py → gis_slots`):
- SBIS: bungalows (required), signals, crossings, turnouts, diamonds, derails, generators, wayside detectors, crossing structures
- CIV: OID frames (required), asset markers, track centerline
- TIVS: inventory sources (asset type–specific), turnout/wayside era pairs
- CVS: corridor segments

**Sync workflow** (initiated by):
- Manual: `/p/{code}/data` → "Sync Now" button
- Scheduled: `scheduled_gis_resync` cron task (configurable per project)
- Health: `probe_gis_reachability` cron task

---

## Configuration & Settings

### Project-Level Configuration

| Surface | Module | Location | Admin tier |
|---------|--------|----------|-----------|
| **Bungalow naming, GIS mapping, equipment order** | SBIS | `/sbis/settings` | Project admin |
| **Equipment catalog** | SBIS | `/sbis/catalog` | Project admin |
| **Unit templates** | SBIS | `/sbis/main-systems/templates` | Project admin |
| **Imagery resolver, viewer, asset markers** | CIV | `/civ/settings` | Project admin |
| **Cost books, reference data** | TIVS | `/tivs/settings` | Project admin |
| **GIS dataset bindings** | Core | `/p/{code}/data#wiring` | Platform admin |
| **Module enablement** | Core | `/admin/projects/{id}` | Platform admin |
| **Fee structure, property scope** | PM | `/pm/fees`, `/pm/properties` | Project admin |

### Environment Variables

(See `.env.example` for full contract)
- `RMI_DEV_USER_SUBJECT`: Local dev identity
- `ARCGIS_PORTAL_URL`, `ARCGIS_CLIENT_ID`, `ARCGIS_CLIENT_SECRET`: Portal OAuth
- `RMI_DATABASE_URL`, `RMI_TEST_DATABASE_URL`: Postgres
- `REDIS_URL`: ARQ broker
- `RMI_STORAGE_BACKEND` (local/s3), `RMI_S3_BUCKET`: Storage
- `RMI_METRICS_TOKEN`: Prometheus metrics (optional)
- Many others (secrets, SMTP, logging, etc.)

---

## Code Quality & CI/CD

**Tooling** (ADR 0001):
- **Lint/Format**: `ruff` (no autopep8, no black)
- **Type check**: `pyright`
- **Test**: `pytest` (no infra required, async-native)
- **Git flow**: Short-lived branches, PR required, squash-merge, main always deployable

**CI Gate** (GitHub Actions):
```bash
ruff check . && ruff format --check .
pyright
pytest
python scripts/alembic_drift.py
```

**Commit discipline** (ADR 0006):
- Conventional commits scoped by module: `feat(tivs): …`, `fix(sbis): …`, `docs: …`
- Multi-line messages via file: `git commit -F <file>`
- Stacked PRs merge bottom-up; rebase children after parent squash

**Documentation**:
- **ADRs** (docs/adr/): Settled decisions, indexed in README.md
- **Planning** (docs/planning/): Roadmap (generated from roadmap.yaml), owner rulings, release notes
- **Code**: Docstrings state *why*, not *what*; correlation context in logs

---

## Known Issues & Future Work

(From CLAUDE.md and README.md)

- **Legacy CVS sunset**: Operational step — bind 25-320 in production, migrate reference data through Excel round-trip, confirm vs. golden, flip read-only.
- **Schema-2 full adoption**: Schema-1 (old interim per-track detector layers) retiring with #1628; Schema-2 merged detector layer + equipment table now canonical.
- **Parity era closed**: #419 closed; no longer gated against golden CTVS. Validation is sense-review with Signal Engineers.
- **Client portal** (future): Restricted access for client contacts without ArcGIS accounts (data model anticipates it).
- **Platform polish**: Shared design system, RMI + railroad branding, export layouts for CIV.

---

## Version & Production URL

- **Current**: v1.62.2 (as of 2026-09-30; was v1.59.1 when first written)
- **Production**: https://apps.rmigis.cloud
- **Health**: `/health` (platform core)
- **Metrics**: `/metrics` (if `RMI_METRICS_TOKEN` set, Prometheus format)
