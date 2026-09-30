# GIS Tools and Tiling Inventory

**Repositories**: `~/sources/rmigis-pyt`, `~/sources/rmi-imagery-tiling`  
**Status**: Both production (rmigis-pyt upgrading the old toolbox; rmi-imagery-tiling live on AWS Lambda)  
**Tech stacks**:
- **rmigis-pyt**: Python 3.13, ArcGIS Pro 3.7, Pydantic, PyYAML, pytest, pyright, ruff, container image via ECR
- **rmi-imagery-tiling**: Python 3.12, pyvips (libvips), boto3, pytest, Lambda + S3 (AWS)

---

## Overview

Two independent tools sit outside rmi-platform but serve GIS needs the platform depends on:

- **rmigis-pyt**: Ground-up rewrite of `rmigis-agp-toolbox`; the ArcGIS Pro Python Toolbox for GIS-side infrastructure (project setup, feature class creation, domain sync, publishing, EGDB backup). Used by GIS admins; platform reads the results. ~24 tools across 6 categories.

- **rmi-imagery-tiling**: Serverless AWS pipeline converting 12288×6144 equirectangular 360° panoramas to multiresolution tiles, published to S3 for streaming by rmi-platform's CIV (Corridor Imagery Viewer) module. Deployed on Lambda; event-driven backfill.

**Platform integration** is **read-only and asynchronous**: platform consumes outputs (EGDB schemas via Portal feature services, tiles via HTTP GET), never writes back. Both tools operate independently of platform runtime.

---

## rmigis-pyt: ArcGIS Pro Python Toolbox (Ground-up Rewrite)

**Repository**: `~/sources/rmigis-pyt`  
**Status**: Production. Replacing `../rmigis-agp-toolbox` tool-by-tool. Pilot 3 tools (Project County/Zone ID, Create Track Improvement FC, Backup EGDB) live; others in migration. Old toolbox still authoritative until each cutover.

**Documentation**: [Wiki](https://github.com/camrex/rmigis-pyt/wiki) (Home, Status, Architecture, per-tool docs, runbooks); README limited to quick start. [CLAUDE.md](/home/rebuild/sources/rmigis-pyt/CLAUDE.md): developer guidance, architecture, environment setup, pitfalls.

### Architecture

**Purity separation** (enforced via ruff and pyright):

- **`src/rmigis/core/`** — pure Python, no arcpy/arcgis imports. YAML schema models/loader/validation, planning/diffing logic, settings (Pydantic + YAML), project/database/backup/publish logic. All tested headless; CI runs on linux with no ArcGIS.
- **`src/rmigis/adapters/`** — the ONLY code importing arcpy or arcgis (single exception: `tools/params.py` for `Param.to_arcpy()` construction). Adapters execute decisions; core makes them. Lazy imports inside functions (fast toolbox load, mockable for tests).
- **`src/rmigis/tools/`** — one module per tool; declarative parameter specs, optional update hooks, thin execute = core plan → adapter apply. `params.py` factories replace hand-written Parameter blocks.

**Tool registration** (`registry.py`): defensive-but-loud per-tool loading; a broken tool is skipped, its traceback recorded in `LOAD_FAILURES`, printed to stderr — never silent.

**Configuration** (Pydantic): `config/settings.yaml` (committed defaults) + `config/settings.local.yaml` (untracked per-machine overlay, never committed). Environment override via `RMIGIS_SETTINGS`.

### Tools (~24, across 6 categories)

Ported from the old toolbox; capabilities preserved, architecture rewritten. Phase 1 migration pilots: Project County/Zone ID, Create Track Improvement Feature Classes, Backup EGDB to FGDB.

**Project Setup** (database, connection files, Portal group, datastore):
- `create_project.py` — six independently-toggleable stages (DB, connections, Portal group, datastore); dry-run defaults on, prints exact DDL and connection specs before applying anything.
- `project_id.py` — County/Zone lookup from a point geometry.

**Feature Class Creation** (YAML-driven schema generation):
- `create_features.py` — read YAML bundle, create FGDB, apply domains/topology, copy to EGDB.
- `bundles.py` — enumerate available schema bundles (Track Improvement, Real Property, Building & Site, plus custom).

**Field Sync**:
- `apply_schema_fields.py` — apply new/removed fields to a live feature service; dry-run supported, backup + service restart.
- `field_defs.py` — export/import field catalog spreadsheet.
- `sync_domains.py` — safe additive-by-default domain sync to a service.

**Data Management**:
- `backup_egdb.py` — copy selected EGDB feature classes to timestamped FGDB; optional domains-YAML export; replace-existing safety (refuses silent overwrite).
- `load_egdb.py` — bulk load a staging table into EGDB feature class (appends or replaces).
- `export_domains.py`, `import_domains.py` — domain list ↔ Excel admin.

**Publishing**:
- `publish_services.py` — publish selected feature classes as feature services on Portal.
- `manage_services.py` — stop/start/test services.

**Real Property & Parcel**:
- `real_prop.py` — real property workflow (parcel etl, sale query, CoStar integration).
- `parcel_etl.py` — parcel load pipeline.
- `costar.py` — CoStar data fetch and landing.
- `sale_query.py` — sale data query.

**Admin**:
- `project_manifest_editor.py` — edit project binding manifest (paths, EGDB, Portal items).
- `set_passwords.py` — keyring password mgmt (service name: `rmigis_pyt`).
- `audit_services.py` — read Portal services, compare with YAML schemas, report field additions/removals/renames.

**Map Authoring**:
- `create_map.py` — create a web map on Portal.
- `map_style.py` — read layer styles from a map.

### Code Structure

```
rmigis.pyt                             # Thin entry point; inserts src/ on sys.path
src/rmigis/
  core/                                # Pure logic (~5KB lines)
    config.py                          # Settings (Pydantic, YAML)
    schema/
      models.py, loader.py, ...        # YAML schema parsing, field/domain models
    project_setup.py                   # Create Project stages
    backup.py, publish.py, ...         # Feature class and domain logic
    project_manifest.py                # Manifest I/O
    outcome.py                         # ToolOutcome (partial success reporting)
  adapters/                            # ArcGIS interface (~2KB lines)
    portal.py                          # ArcGIS Portal API (OAuth, items, services)
    egdb.py, postgres.py               # Enterprise GDB, PostgreSQL connection
    workspace.py, fc_builder.py        # Feature class operations
    publishing.py                      # Publish workflow
    excel.py, csv.py                   # Excel/CSV adapters
    requirements.py                    # Runtime-only dependency checks (psycopg2)
  tools/                               # Tool UI + execution (~2KB lines)
    base.py                            # BaseTool (updateParameters, updateMessages, execute)
    params.py                          # Parameter spec factories (replace hand-written blocks)
    create_project.py, ...             # One module per tool
    dialog.py                          # updateParameters helpers (picker caching)
  registry.py                          # Tool registration, load_failures tracking
  testing.py                           # Test fixtures
config/
  settings.yaml                        # Committed defaults (Portal URL, EGDB host, etc.)
  settings.local.example.yaml          # Template for per-machine overlay
templates/                             # YAML schema bundles (ported from old toolbox)
  track_improvement/
    _shared.yaml                       # Metadata
    xing_inv_pt_field_catalog.yaml     # Field definitions (with inheritance)
    xing_inv_pt_domains.yaml           # Coded-value domains
    ...                                # 21 FCs total across three domains
typings/arcpy/                         # Minimal stubs for pyright (no full ArcGIS install needed for CI)
tests/
  core/                                # Pure logic tests (no arcpy needed)
  adapters/                            # Adapter contract tests (arcpy mocked by default, real arcpy with `pytest -m arcpy` on the dev box)
  tools/                               # Dialog layer tests
```

### Key Patterns & Decisions

**Manifest-driven setup** (`ProjectManifest`, `manifest.py`): project paths, EGDB connection spec, Portal items, GIS dataset bindings. Stores once, used by all tools. Closes the gap where the old toolbox required multiple conventions (different projects kept connection files in different places).

**Dry run as default safety** (not opt-in): `create_project.py` prints DDL and manifests before applying; explicit untick applies it. Reverses the old tool's "default on, no dry run" posture.

**Partial-success tracking** (`ToolOutcome`): a tool that fails to create 5 of 6 feature classes reports "4 succeeded, 1 failed" — not "all-or-nothing success/fail".

**Settings validation** (Pydantic, `extra="forbid"`): misspelled keys fail fast, not silently.

**No per-tool cutover blockers yet** (Phase 1 pilot is 3 of ~24): tools are feature-complete (rewritten from old), but production cutover awaits per-tool validation (smoke tests at the office against real EGDB / Portal).

### Platform Integration

**What platform consumes**: The EGDB schemas created by this toolbox (feature classes, domains, topology) land as ArcGIS Portal feature services. Platform's GIS sync reads those services and lands attributes in Alembic-defined tables (one per dataset; `gis_dataset_synced_<dataset>`). Platform never writes back.

**Seam**: ArcGIS Portal → platform-core GIS sync (`platform_core/arcgis/synced.py`) reads the feature service layers this toolbox publishes.

**How to use** (GIS admin workflow):
1. Run rmigis-pyt tools to set up project in EGDB, publish feature services to Portal.
2. Admin binds services at `/p/{code}/data#wiring` in rmi-platform (maps `GisSlot` to `GisDatasetBinding`).
3. Platform's worker enqueues sync (reads feature service, lands in `gis_dataset_synced_*` tables).
4. Modules read synced data instead of hitting Portal directly.

### Development & Deployment

**Local dev** (Windows, ArcGIS Pro 3.7 install):
- `scripts/setup_env.ps1` — clones Pro's `arcgispro-py3` to `E:\envs\rmigis-pyt`, installs deps + dev tools, editable-installs repo.
- `proswap E:\envs\rmigis-pyt` — activate in ArcGIS Pro via Package Manager.
- `python.exe -m pytest` — tests run headless (no ArcGIS); `pytest -m arcpy` runs against real arcpy on the dev box (office IP only, #79).
- CI (GitHub Actions, ubuntu): `ruff check`, `ruff format --check`, `pyright`, `pytest` (no ArcGIS).

**Three-role environment distinction** (CLAUDE.md): Pro runtime, GIS dev/test (both inherit arcpy from Pro's conda), non-GIS dev (mirrors CI exactly, no ArcGIS). The dev box is richer than CI, which has bitten three times; keep an eye on imports (`typings/arcpy/` truthfulness).

**Deployment**: No separate deploy step. The `.pyt` loads the repo from the working tree (fast, editable), so Pro smoke-tests exercise the checked-out branch directly.

---

## rmi-imagery-tiling: Serverless Tiling Pipeline for 360° Panoramas

**Repository**: `~/sources/rmi-imagery-tiling`  
**Status**: Production. Deployed to AWS (us-east-2) 2026-07-02; all three projects (RMI25320, RMI25340, RMI26150) backfilled and validated; event trigger live on rmi-360-prod.

**Documentation**: README (quick start, architecture, contract, deploy steps); `docs/SPEC.md` (full requirements, quality bar); `docs/RUNBOOK.md` (console deploy, backfill, retry, validate, lifecycle, cost).

### Purpose

Convert full-resolution equirectangular 360° panoramas (12288×6144 JPEGs in S3 bucket `rmi-360-prod`) to multiresolution tiles for progressive streaming by rmi-platform's CIV (Corridor Imagery Viewer). Originals never modified, moved, or renamed — the Esri Oriented Imagery Dataset points at them. Derived objects fully regenerable; entire derived bucket deletable and re-runnable.

**Scope**: Panorama → tiles only. Out of scope: Esri OID, ImagePath references, originals, secured bucket `rmi-oid-corridor-imagery` (us-east-1).

### Architecture

**Pure core / thin adapter pattern** (like rmigis-pyt):

- **`src/rmi_tiling/`** — no boto3 imports. Pure logic for key parsing, tiling geometry, event normalization.
  - `keys.py` — `SourceKey` model: parse `{project}/{filename}.jpg` into `(project, stem)`, derive all 129 output keys.
  - `tiler.py` — `generate_derived_objects()`: one pyvips image → (base.jpg 2048×1024, 128 tiles 768×768); concurrent encode; fails whole frame if source wrong dimensions.
  - `events.py` — `normalize()`: detect S3 Batch Ops v1.0/v2.0, S3 notification, direct invoke; extract tasks; recursion guard.

- **`src/rmi_tiling_aws/handler.py`** — the ONLY boto3 importer. Lambda wrapper: GET source, HEAD check (idempotency), call `tiler.generate_derived_objects()`, PUT 129 objects with cache headers, return Batch-compliant result code or raise.

**No AWS dependencies in core**: tests run locally without credentials. `RMI_TILING_SAMPLE=<path>` env var runs integration tests against a real panorama instead of the generated gradient sample.

### The Tile Contract: `tile-contract.v1.json`

**Authoritative single source** between tiling pipeline and rmi-platform CIV. Per frame:

```json
{
  "contractVersion": 1,
  "source": { "width": 12288, "height": 6144, "format": "jpeg" },
  "derivedRoot": "s3://rmi-360-derived (us-east-2, separate bucket, public read + CORS)",
  "base": { "width": 2048, "height": 1024, "quality": 80, "key": "{derivedRoot}/{project}/{stem}/base.jpg" },
  "tiles": {
    "size": 768, "cols": 16, "rows": 8, "quality": 80,
    "key": "{derivedRoot}/{project}/{stem}/tiles/{col}_{row}.jpg",
    "colRange": "0-15 left to right", "rowRange": "0-7 top to bottom"
  },
  "objectsPerFrame": 129,
  "cacheControl": "public, max-age=31536000, immutable"
}
```

**Any change is a new `contractVersion`, never an edit.** Tests (`tests/test_contract.py`) enforce code↔contract consistency.

### Components

**1. Tiling core** (`src/rmi_tiling/`):
- `keys.py` — key derivation; parse source key, derive all 129 relative keys. Handles multi-dot stems (milepost like `G0.668`, `R275.741`).
- `tiler.py` — `generate_derived_objects(source_path)`: open JPEG with pyvips, validate 12288×6144, copy to memory (unlocks concurrent crops), encode base (2048×1024 q80, 1/6 resize) + 128 tiles (768×768 crops, q80) in parallel (8 workers). Strips EXIF (lean tiles). Any error fails whole frame.
- `events.py` — normalize S3 Batch Ops v1.0/v2.0, S3 notifications, direct invoke to `(bucket, key, task_id, force_flag)` tuples.

**2. Lambda wrapper** (`src/rmi_tiling_aws/handler.py`, container image x86_64):
- `lambda_handler(event, context)` — normalize event, iterate tasks, for each: GET source from `rmi-360-prod` to `/tmp`, check recursion guard, call `generate_derived_objects()`, HEAD `base.jpg` in derived bucket (skip if present, force if flag set), PUT all 129 objects with `image/jpeg` + contract cache header, return result code.
- Result codes (Batch Ops compatible): `Succeeded`, `TemporaryFailure` (retried by Batch), `PermanentFailure` (bad key, wrong dimensions, missing source).
- Structured JSON logging: stem, outcome, duration_ms, bytes_in/out per frame.
- Memory 3008MB, timeout 120s, reserved concurrency 200 (measured ~7 s/frame).

**3. Recursion guard** (hardened):
- Structural: notification rule on `rmi-360-prod`, all writes to `rmi-360-derived` (separate bucket, no notification). One bucket-wide rule, recursion structurally impossible.
- Code-level: `events.check_recursion_guard()` refuses any event where bucket == derived bucket, or key shaped like derived output (`{project}/{stem}/base.jpg` or `.../tiles/{c}_{r}.jpg`).

**4. Infrastructure as Code** (`terraform/`):
- ECR repo, Lambda + least-privilege role (GetObject rmi-360-prod, PutObject+ListBucket rmi-360-derived, CloudWatch logs), derived bucket (public-read+CORS), ops bucket (private, manifests/reports), event notification on originals, GLACIER_IR-60d lifecycle on originals, Batch Operations role.
- Terraform produces: Lambda ARN, Batch role ARN, ops bucket name.
- Console runbook also provided (step-by-step equivalent, no Terraform).

**5. Backfill & Operations** (`scripts/`):
- `prepare_backfill_manifest.py` — pure S3 ListObjectsV2 walk of `rmi-360-prod`, optional `--project` filter, emit Batch Operations CSV. No toolbox manifests consulted.
- `dry_run.py` — pre-backfill smoke test: tile ~10 real frames end-to-end through deployed Lambda, validate exactly those stems.
- `retry_failures.py` — parse Batch completion report, emit manifest of failed keys.
- `validate_tiles.py` — fleet totals (original count vs. distinct derived stems), sample N random stems, deep-check each (all 129 objects present, base + 3 random tiles downloaded, verify JPEG format/dimensions/cache header).

### Code Structure

```
src/
  rmi_tiling/                          # Pure, no boto3
    keys.py                            # SourceKey model, key derivation
    tiler.py                           # generate_derived_objects: pyvips tiling core
    events.py                          # Event normalization, recursion guard
    __init__.py
  rmi_tiling_aws/                      # boto3 only here
    handler.py                         # Lambda entry point
    __init__.py
scripts/
  prepare_backfill_manifest.py         # S3 ListObjectsV2 walk → CSV
  dry_run.py                           # Smoke test: tile ~10 keys, validate
  retry_failures.py                    # Parse report, emit retry manifest
  validate_tiles.py                    # Fleet audit + sampled deep checks
terraform/                             # ECR, Lambda, buckets, roles, lifecycle, Batch role
  main.tf, variables.tf, outputs.tf    # IaC for full stack
docs/
  SPEC.md                              # Original build spec, phases 1–5, amendments
  RUNBOOK.md                           # Deploy, backfill, retry, validate, lifecycle
tests/
  test_keys.py                         # Key parsing, multi-dot stems
  test_tiler.py                        # Tiling geometry, dimensions
  test_events.py                       # Event normalization, recursion guard
  test_handler.py                      # Lambda wrapper, idempotency, logging
  test_contract.py                     # Enforces code↔contract consistency
  test_scripts.py                      # Manifest prep, validation
tile-contract.v1.json                  # Authoritative contract (shared with platform)
Dockerfile                             # x86_64: python:3.12-slim + libvips42 + pyvips + awslambdaric
```

### Key Patterns & Decisions

**Idempotency via HEAD short-circuit** — cheap insurance for S3 notification duplicates. Default force=false during backfill; frames with existing `base.jpg` skip after one HEAD. Re-running the manifest is cheap and safe.

**Failures are whole-frame** — no partial success. Any error (bad source dimensions, missing key, tile encode failure) fails the entire 129-object set. Overwrites idempotent; retries regenerate all 129 harmlessly.

**Separate derived bucket** (decided, CLAUDE.md amendment 1): `rmi-360-derived` same region, public-read+CORS posture mirrors originals. Recursion structurally impossible; new projects require zero notification changes; lifecycle scoping clean.

**Force flag via env + user arguments** — Batch Operations schema 2.0 can pass `userArguments: {"force": "true"}`; env var `RMI_TILING_FORCE` applies locally; backfill default is force off.

**Lifecycle on originals only** — originals transition to GLACIER_IR after 60 days (one bucket-wide rule). Derived bucket never transitions (hot serving assets, ~40KB each). Versioning verified not enabled on originals (2026-07-02).

**Tests generate sample, never commit 18MB panorama** — `tests/` build a full-size gradient sample locally; `RMI_TILING_SAMPLE=<path>` runs the same suite against a real frame for integration validation.

### Production Deployment & Status

**Deployed 2026-07-02** to account 987980910568, us-east-2. Event trigger LIVE on `rmi-360-prod`.

**Fleet backfill complete** (zero failed tasks across both jobs):
- RMI25320 + RMI25340: 113,694 frames (Batch job 17382f00-...)
- RMI26150: 51,110 frames (Batch job bf6449cc-..., plus event trigger for in-flight upload tail)

**Performance** (measured in-container post-optimization):
- ~7 s/frame (was ~20 s before parallel encode + copy_memory optimization)
- ~100K frames/hour at reserved concurrency 200
- Total fleet: ~$18 Lambda + ~$33 PUTs + ~$0.30 Batch + ~$7/month storage

**Steady state**: event trigger tiles new uploads automatically; no scheduled work pending. New projects require zero config changes (manifest-free design).

### Platform Integration

**What platform consumes**: The tile URLs derived from the contract (`{project}/{stem}/base.jpg`, `{project}/{stem}/tiles/{col}_{row}.jpg`).

**Seam**: CIV module (`modules/civ/src/civ/`):
- `pano.py` — `tile_root()` derives the frame's tile-contract.v1 root from OID imagepath (pure string manipulation, no AWS calls).
- `settings.py` — project-scoped viewer config:
  - `IMAGE_RESOLVER_KEY = "image_resolver"` — client strategy ("direct" today; "tiles-v1" once tiles exist).
  - `TILES_BASE_URL_KEY = "tiles_base_url"` — the derived bucket root URL (contract `derivedRoot`, e.g., `https://rmi-360-derived.s3.us-east-2.amazonaws.com`).
  - `FRAME_SOURCE_KEY = "frame_source"` — where frames come from ("synced" = landed OID rows, "live" = feature service).
  - `PANO_CARD_RADIUS_KEY = "pano_card_radius_m"`, `PANO_CARD_STANDOFF_KEY = "pano_card_standoff_m"` — embedded 360° card geometry (asset lookup radius, standoff for on-track assets).

**How to use** (operator workflow):
1. Operator uploads panoramas to `rmi-360-prod` (per-project folder).
2. Event trigger fires, Lambda tiles each frame (~7 s), PUTs to `rmi-360-derived`.
3. At `/p/{code}/settings#imagery`, operator sets:
   - `image_resolver` = "tiles-v1"
   - `tiles_base_url` = "https://rmi-360-derived.s3.us-east-2.amazonaws.com"
4. CIV viewer now streams tiles instead of full 12288×6144 images.
5. SBIS asset cards embed the panorama (resolves nearest camera frame, computes bearing to asset, opens panorama on that heading).

**Why CIV doesn't import tiling code**: Platform is frontend and operator UI; tiling is production infrastructure (Lambda + S3). Contract is JSON on disk (`tile-contract.v1.json`) and environment config (`tiles_base_url`). Separation keeps CIV decoupled from AWS operations.

---

## What Platform Could Use (Future Integration Points)

### From rmigis-pyt
1. **Schema validation library** — the core's Pydantic models + YAML loader are general-purpose. Potential extraction: `rmigis.core.schema` as a standalone package for platform to validate schemas against definitions. Currently read-only: platform just syncs what Portal publishes.

2. **Field/domain synchronization patterns** — the `field_sync.py` and `domain_diff.py` logic (additive-safe diffing, dry-run, rollback on error) could inform any future platform ↔ Portal attribute updates (today forbidden by MISSION.md; deferred change queue (#851) is planned, which would benefit from battle-tested logic).

3. **Credential and authentication** — the keyring pattern (`rmigis.adapters.credentials`) and `credentials.py` (service name, get/set) could standardize secrets mgmt across tools if platform needs GIS-side credentials (unlikely given read-only sync, but Portal OAuth refresh is a seam).

### From rmi-imagery-tiling
1. **Async tile generation** — if platform ever captures new panoramas (outside CIV scope today), Lambda + event trigger is a proven pattern for async image processing. Extraction: core tiler (`src/rmi_tiling/tiler.py`, `keys.py`) is pure and deployable elsewhere.

2. **Contract-driven development** — `tile-contract.v1.json` is the model. Similar contracts could govern:
   - Feature service schema (what fields, types, domains a module expects from Portal).
   - Report PDF structure (provenance, sections, page breaks).
   - GIS slot schema (required fields per bungalow/asset/crossing).

3. **Idempotency patterns** — HEAD short-circuit (skip if already done) is broadly applicable to async platform tasks (document generation, report export, data backups). Could standardize on S3 ETags or DB `last_updated` checks.

---

## Seams with rmi-platform

### GIS Sync Seam (rmigis-pyt → platform)
1. **Input**: Feature services created and published by rmigis-pyt tools.
2. **Processing**: Platform's GIS sync (`platform_core.arcgis.synced.py`) reads services (Portal client), validates schema, lands attributes in Alembic tables.
3. **Output**: Modules read synced data.
4. **Failure mode**: Service unavailable → `GisSyncGap` recorded, oldest sync run tracked; modules degrade gracefully.

### Imagery Seam (rmi-imagery-tiling → platform)
1. **Input**: Tile URLs derived from CIV OID imagepath + project settings (tiles_base_url, resolver strategy).
2. **Processing**: CIV viewer (`civ.web.static.viewer.js`) fetches base + tiles on-demand (progressive streaming, CORS direct S3 GETs).
3. **Output**: Panorama streams to browser; SBIS asset cards embed tiles.
4. **Failure mode**: Tiles unavailable → viewer opens full imagepath (CIV fallback), no error on asset card.

---

## Known Limitations & Future Work

### rmigis-pyt
- **No headless runbook yet** — tools require ArcGIS Pro GUI; no command-line CLI (design decision: too many stateful dialogs).
- **Per-tool cutover in flight** — ~24 tools live; Pilot 3 (3 tools) in migration; others await office-based smoke tests against real EGDB/Portal.
- **Conditional imports on dev box** — the GIS dev env inherits arcpy from Pro's conda; non-GIS CI has no ArcGIS. Gap caught in CI (headless tests fail), not locally (dev box has more). Could be closed with a pure Python venv.
- **Topology disabled** — suspended in `rmigis-agp-toolbox`; complete YAML design in `rmigis-pyt` but ArcGIS Pro compatibility issue blocks re-enablement.

### rmi-imagery-tiling
- **x86_64 only** — arm64 cost savings negligible at this scale; Windows cross-builds slow. Decision stands.
- **No manifest caching** — backfill manifest is pure ListObjectsV2 walk every time. Tolerable for ~200K-frame fleets; could cache project contents for very large catalogs.
- **Sample image generated, not real** — tests create a gradient; RMI_TILING_SAMPLE env var runs against real frames. Keeps repo footprint small but loses pre-flight validation of real imagery.

---

## Key Files & Paths

### rmigis-pyt
- `README.md` — quick start
- `CLAUDE.md` — developer guide, architecture, environment, pitfalls
- `CONTRIBUTING.md` — process, branching, standards
- `src/rmigis/registry.py` — tool registration
- `src/rmigis/core/` — pure logic modules
- `src/rmigis/adapters/` — ArcGIS interface modules
- `src/rmigis/tools/` — tool implementations (one per file)
- `config/settings.yaml` — committed defaults
- `templates/` — YAML schema bundles
- `tests/` — pytest suite (headless core, mocked adapters, arcpy contract suite)

### rmi-imagery-tiling
- `README.md` — architecture diagram, contract, quick start
- `CLAUDE.md` — project context, status, decisions, development
- `docs/SPEC.md` — build spec, phases, quality bar
- `docs/RUNBOOK.md` — deploy, backfill, retry, validate, lifecycle, cost
- `src/rmi_tiling/keys.py` — key derivation
- `src/rmi_tiling/tiler.py` — tiling core
- `src/rmi_tiling/events.py` — event normalization, recursion guard
- `src/rmi_tiling_aws/handler.py` — Lambda wrapper
- `terraform/` — infrastructure as code
- `scripts/` — backfill, retry, validation utilities
- `tile-contract.v1.json` — authoritative contract (shared with platform)
- `tests/` — pytest suite (pure, no AWS)

