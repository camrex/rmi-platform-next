---
status: superseded
kind: architecture
date: 2026-08-14
refs: []
source_status: "Superseded by 0016 + 0023 (2026-08-14 — historical, see the amendment below) · originally Accepted (2026-06-06) · Amended (2026-06-07) · Amended (2026-07-12) · Amended (2026-07-13) · Amended (2026-07-23) · Amended (2026-08-14) · Amended (2026-09-17)"
imported_from: rmi-platform/docs/adr/0007-arcgis-feature-service-integration.md
imported_on: 2026-10-03
---
# 0007 — ArcGIS Enterprise feature-service integration

**Status**: Superseded by 0016 + 0023 (2026-08-14 — historical, see the amendment below) · originally Accepted (2026-06-06) · Amended (2026-06-07) · Amended (2026-07-12) · Amended (2026-07-13) · Amended (2026-07-23) · Amended (2026-08-14) · Amended (2026-09-17)

## Amendment (2026-09-17) — the corrections deliverable keys on `asset_id` (#1910)

Owner ruling 2026-09-17. The GIS-corrections CSV described in *Amendment
(2026-06-07c)* below, its per-field workbook from issue #24
(`/sbis/reconcile-corrections.xlsx`) and the differences CSV
(`/sbis/reconcile.csv`) head their first column —
the asset id the GIS team joins on — **`asset_id`**, not `bglw_id`. The values
are unchanged; only the column name is.

Why: `bglw_id` named `sbis.bungalow.bglw_id`, the stored copy of the asset id that
**#1472 dropped** — the id is now resolved from the synced GIS row, where the
attribute has always been `asset_id`. The SBIS JSON API renamed to `asset_id` in
v1.54.0 (#1473) and the xlsx inventory export in #1910, both with no deprecation
window; this closes the last surface that disagreed. **No deprecation window and
no aliased duplicate column here either**: a saved ArcGIS join or query reading
`bglw_id` must be repointed to `asset_id`.

This supersedes the `bglw_id` column name in *Amendment (2026-06-07c)*. The
`sbis.gis_field_ack` table's own key naming is untouched — that is storage, not a
delivered header.

## Amendment (2026-08-14) — retired to a historical record by ADR 0023

[ADR 0023](0023-gis-ingestion-contract.md) states the GIS ingestion contract
(who fetches, cadence, refusal semantics, sync control, identity). With the
four clauses below already superseded by ADR 0016, this document's remaining
unique content is the mechanical layer — service/folder resolution, the
client, contracts/landing, `/admin/gis` binding — which moves to reference
documentation as follow-up work. **This ADR is historical: no new decision
should cite it as authority.** Current authority: ADR 0016 (posture),
ADR 0023 (ingestion contract).

## Amendment (2026-07-23) — access posture refined by ADR 0016 (#407/#408)

[ADR 0016](0016-gis-data-access-posture.md) (Proposed then; Accepted
2026-07-28) refines four clauses of
this ADR; none stands as written once 0016 is accepted:

1. **#141 "slots declare consumption"**: slot declaration remains the
   binding/sync declaration but is no longer a read gate — every enabled module
   may read any project-bound dataset (0016 §1).
2. **#142 point 5 "TIVS keeps its own typed sync"**: revised toward one Portal
   fetch per layer per cycle (#451); module typed tables become derivations,
   not independent fetches (0016 §2).
3. **Consequences "sync is incremental via the editDate watermark"**: the
   shipped platform sync is full-refresh; #9's watermark sync-in is the path
   back to the original intent (0016 §2).
4. **Deferred "`apply_edits()` write-back (build when a module needs it)"**:
   tightened — write-back is Deliberate and Guarded, per-module allow-list,
   per-project opt-in, field-ownership-governed, dry-run-first, audited
   (0016 §4). Decision §3's "when a module (likely TIVS/CVS) needs it"
   expectation is superseded on the consumer too: the likely first
   implementation is SBIS (0016 §4).

## Amendment (2026-07-13) — synced dataset attributes are platform-owned (#142)

With datasets as the binding grain (#141), the shared-attribute half of plan §6
lands: TIVS's Wave 0 "fetch → validate → land" sync core is promoted into
`platform_core` as a **project-dataset service**, so modules read a dataset's
attributes from one platform-synced table instead of each fetching the feature
service independently — one sync cadence, one drift-detection point, one
provenance stamp. Attribute data only; maps stay on feature services / the
ArcGIS JS SDK client-side (that model works well and is unchanged).

**Decision:**

1. **The pure landing core moves to `platform_core.arcgis.landing`** (contract
   validation, row planning, domain-label decoding, layer field schema). TIVS
   re-exports it from `tivs.inventory.contract`; its calc-critical column
   mapping, typed landing tables, and per-source run reports stay module-owned
   (the module knows *which* fields matter, the platform knows *how* to land).
2. **One synced table per (project, dataset)** — `platform.gis_dataset_row`:
   the full attribute map verbatim (JSONB passthrough, the audit source) plus
   decoded coded-value labels. Row identity is the layer's **GlobalID** when it
   declares one — OBJECTIDs can be reassigned on reloads/compress — with the
   OBJECTID as fallback identity (and riding along for OID-keyed lookups). No
   typed columns: a module that needs them declares its own contract and tables.
3. **Run reports mirror the TIVS pattern** — `gis_dataset_sync_run` /
   `gis_dataset_sync_gap` record counts, per-record gaps, the layer's field
   schema at sync time, and provenance (platform version + git SHA + who asked).
   Landing is a full refresh per (project, dataset), advisory-locked, in one
   transaction; schema violations fail loud and land nothing.
4. **The worker task is platform-owned.** `sync_gis_datasets` registers in
   `platform_core.worker.settings.WorkerSettings` (not the composition root): it
   reads only dataset *bindings* (DB rows), never module manifests. Admin
   triggers it per project from `/admin/gis`, which also shows per-dataset
   freshness.
5. **Modules consume via `platform_core.arcgis.synced`** (`dataset_rows`,
   `latest_sync_run`) and never see URLs or tokens. TIVS keeps its own typed
   sync — its era-variant sources aren't datasets, and its run reports feed
   module UI.
6. **Bungalows are a project dataset** (decided 2026-07-13, revising the
   2026-07-12 "seed layer stays module-specific" hedge): SBIS's `bungalow`
   slot, CIV's `bungalow` marker slot, and TIVS's `bungalow_inv_pt` source all
   consume `bungalows` — the layer is era-identical, so the shared dataset
   erases no era signal, and the module rows were the same drift-prone
   multi-bind #141 removed elsewhere (live data had the layer bound three ways).
   The first consumer is **SBIS reconciliation**: its comparison view reads
   the platform-synced attributes (as-of-last-sync, provenance-stamped, no
   full-layer fetch per page load) with a sync trigger + freshness on the
   page; the single-cell **apply** path stays live (fetch one feature, then
   write). CIV/SBIS search-over-attributes surfaces remain future consumers.

## Amendment (2026-07-12) — bind once per (project, dataset); modules declare consumption (#141)

Three modules now consume the platform's GIS plumbing, and the per-module slot
model duplicates the same wiring: SBIS declares nine point-layer slots, CIV's
asset-marker slots reuse the **same keys** (`signals`, `crossings`, `turnouts`,
`diamonds`, `derails`, `ontrack_detectors`, `offtrack_detectors`,
`generators`), and TIVS's contract slots cover the same physical layers again
(`signal_inv_pt`, `xing_inv_pt`, `derail_inv_pt`, …). On one project the same
feature layer can be bound three times, by hand, drifting independently — the
duplication predicted in plan §6. This amendment evolves layer 3 of the
2026-06-07 model; layers 1–2 (folder + cached catalog) are untouched.

**Decision — project datasets as the binding grain:**

1. **A dataset is a named physical layer, bound once per project.** New
   platform table `project_gis_dataset` (project, dataset key → service name +
   type + layer id, the same durable identifiers slot bindings use). The
   dataset vocabulary is the union of what module manifests declare — no
   separate registry to drift.
2. **Slots declare consumption.** `GisSlot` gains `dataset: str | None`. A
   slot naming a dataset resolves **exclusively** through the project's
   dataset binding (no per-module override — a module that genuinely needs a
   different layer is declaring a module-specific slot, which is a code
   decision, not an admin toggle). Slots with `dataset=None` stay
   module-specific and bind exactly as today (CIV's `oid` imagery layer,
   SBIS's `bungalow` seed layer if kept distinct).
3. **TIVS's era-alternative sources stay module-level for now.** The active
   turnout link is *selected by which slot is bound*
   (`turnout_inv_pt` vs `turnout_cx_inv_pt`) — collapsing both onto one
   `turnouts` dataset would erase the era signal. Era-stable sources map to
   datasets (`track_cl_inv` → `track_centerline`, `signal_inv_pt` → `signals`,
   `xing_inv_pt` → `crossings`, …); the era pair keeps module slots until era
   selection itself moves platform-side (a separate decision, if ever).
4. **Module resolution API is unchanged.** `resolve_client` /
   `get_binding` / `list_bindings(project, module)` keep their signatures and
   return effective bindings — dataset-resolved slots included — so sync
   tasks, TIVS's `active_link`, and the viewers change nothing.
5. **Migration path — hard cut-over, no runtime fallback** (revised in
   implementation, #141 slice 1: live data shows zero multi-module overlap,
   so a transitional fallback would protect an empty case while silently
   shadowing admin-visible rows — the exact drift this amendment removes).
   A data migration, shipping in the same deployable unit as the manifest
   declarations, promotes existing `project_module_gis_source` rows: where
   every module binding mapping to a dataset agrees on (service, layer), one
   dataset row is written; **all** dataset-mapped module rows retire either
   way. Where bindings disagree the migration never guesses — no dataset row
   is written, the slot is unbound (resolution fails loud), and the migration
   reports what needs a human to bind at `/admin/gis`.
6. **`/admin/gis` UX**: a "Project datasets" section (one dropdown per
   dataset over the cached catalog) above the per-module cards, which shrink
   to module-specific slots.

**Follow-on, explicitly out of scope here:** with datasets as the binding
grain, #142 (shared synced attributes) hangs one synced table per
(project, dataset) and promotes TIVS's sync seam platform-ward (plan §6) —
that is its own slice, designed against this model.

Implementation slices tracked on #141: this amendment → platform table +
dataset-aware resolution → manifests declare datasets + promotion data
migration (one deployable unit) → admin UX.

## Amendment (2026-06-07) — identity proven live; config promoted to a project GIS catalog

Slice 1's probe against the live portal (`maps.rmigis.cloud`) resolved two open
questions and reshaped the config model. This amendment governs where it conflicts
with the original decision below.

**Identity — the platform's own OAuth app, not a separate data app.** App-login
(`client_credentials`) is still the default, but the credential is the **existing SSO
app** (`RMI_ARCGIS_CLIENT_ID`), not a new data-only app. Findings:

- The portal binds this app's tokens to an HTTP **Referer**; requests without
  `Referer: https://apps.rmigis.cloud` (the redirect-URI host) get `498 Invalid
  Token`. The client now sends a configurable `RMI_ARCGIS_REFERER` as a default
  header (token mint + every request).
- App-login tokens are **not group members**, so they `403` on group-shared
  (`access=shared`) services — which is all of `26-150`. Granting the OAuth credential
  the **Content > View All** privilege fixed it (no per-service or org sharing change).
- So `arcgis_data_client_id/secret` are now **optional** and **fall back to the SSO
  app** credential (`effective_arcgis_data_*`). No second app registration, no extra
  Secrets Manager entry. A dedicated data app remains supported if ever wanted.

**Login is gated to a Portal group.** SSO login already enforces
`arcgis_allowed_group` (matched by title against the user's own `community/self`
groups). Set to **`RMI Platform Users`**. (The gate uses the *user's* token, so it is
independent of the app-login privileges above.)

**Config is a project GIS catalog, not settings JSON.** The original
settings-driven `FeatureSource` / `RMI_ARCGIS_SOURCES` becomes the low-level
primitive *under* a DB-backed, project-scoped catalog (this realizes the "promote
FeatureSource into the admin/config registry" deferral). Three layers, each owned by
the layer that knows it:

1. **Project → Portal folder (platform).** `Project.arcgis_folder` (e.g. `26-150`).
   Folder only — service names come from enumeration, not a prefix convention. Portal
   /server base URL stays global platform config.
2. **Available services — platform, cached.** A `platform.arcgis_service` catalog per
   project: service name, layers (id + name), url, schema hash, `last_refreshed`.
   Populated by enumerating the folder (REST folder listing) via an admin "refresh"
   action + a periodic ARQ task. **Modules read the cache, never Portal, for
   discovery.** (Mirrors TIVS's `ArcgisServiceMetadata` incl. schema-hash drift.)
3. **Slot binding — module declares, platform stores, admin wires.** The module
   manifest declares semantic **slots** (SBIS: `bungalow` required, `signal`
   optional). The platform stores the binding per (project, module, slot) in
   `platform.project_module_gis_source` (service + **layer id** — bungalow is layer
   12). The admin UI renders each slot as a dropdown over the project's cached
   catalog. Resolution: `get_arcgis(project, module, slot)` → binding → catalog →
   URL (folder + service + layer + base) → configured app-login client. Modules never
   see URLs or tokens.

**Bungalow field facts (confirmed against the live layer 12, 82 fields, 572
features).** Business key is **`asset_id`** (e.g. `BG-05-000005`) — *not* `bglw_id`,
which does not exist on the service; `globalid` is the stable surrogate. `lat`/`long`
are plain attributes (no centroid math). `last_edited_date` (epoch ms) is the
incremental watermark. Many fields are coded-value domains (`rmi_trk_*`). GIS count
(572) exceeds the SBIS snapshot (440) — a real drift to reconcile on first sync.

**Build order (revised).** Slice 1 (client) done. **Slice 1.5** — project GIS catalog
(folder field, catalog + binding tables, folder enumeration, refresh + resolution,
admin panel) **done**. **Slice 2** — SBIS declares the `bungalow` slot, admin binds it,
then reconciliation. Slice 3 unchanged.

## Amendment (2026-06-07b) — Slice 2 shipped as reconciliation, not auto-sync

Slice 2 went live (prod deploy v4 / `app.8`) as a **human-in-the-loop reconciliation
tool**, deliberately *replacing* the automatic upsert engine that Decision #1 below
made the primary flow. Rationale: GIS and SBIS had already diverged (GIS includes
records SBIS doesn't, and SBIS carries curated values GIS lacks), so silently
overwriting SBIS on a watermark would destroy curation. What shipped:

- `sbis/reconcile.py` (pure engine) + `web/reconcile.py` (`/sbis/reconcile`). A live GIS
  read is compared field-by-field against SBIS using a fixed field map, each field
  carrying a **disposition** (gis_authoritative / clean / sbis_curated / review) that
  sets whether a mismatch is actionable. The unified table offers per-cell **← GIS**
  apply on matched rows and inline **Create** for GIS bungalows missing from SBIS.
  Filter by subdivision/status, sort by milepost; CSV exports; every write audited.
  (The original triage disposition — excluded / no_as_built / other in
  `sbis.gis_disposition` — was retired by #880: the 1:1-with-GIS doctrine of ADR 0018-era
  #825 made every GIS bungalow enter SBIS regardless, so exclusion moved onto the
  bungalow's own Status and the table was dropped.)
- No `gis_sync_state`, no watermark, no `latitude`/`longitude` columns, no ARQ task — the
  reconcile read is on-demand and synchronous.

**Auto-sync is now explicitly deferred** (not cancelled): the `sync.py` engine +
watermark + worker task remain a clean future addition behind the same client/catalog,
should unattended refresh ever be wanted. The reconciliation field map is the de-facto
field-ownership spec it would reuse.

## Amendment (2026-06-07c) — SBIS→GIS direction for the FS-alignment audit

A live audit requires the bungalow feature service to be aligned *to* SBIS at the general
bungalow-data level — i.e. a list of corrections the GIS team must apply. The reconcile
tool was GIS→SBIS only; this amendment adds the reverse read-out without write-back:

- **Field acknowledgements** — a new `sbis.gis_field_ack` table keyed (project, bglw_id,
  field) records a per-cell reviewer decision on a *matched* mismatch:
  `gis_correction_logged` (SBIS is right; FS must change) or `sbis_ok_keep` (reviewed, keep
  SBIS). Acked cells render green; un-acked diffs stay amber — so the open-diff list can be
  driven to zero (apply ← GIS, or acknowledge). Every set is audited
  (`sbis.gis_field_ack.set`).
- **GIS-corrections CSV** (`/sbis/reconcile-corrections.csv`) — the deliverable. Its join
  column is named `asset_id` since the 2026-09-17 amendment above (it read `bglw_id` here).
  Rows carry
  `correction_type ∈ {field, fs_missing_record, include_flag}`. A `field` row is included
  when logged `gis_correction_logged`, or by default when the field is `sbis_curated`;
  excluded when `sbis_ok_keep` or when GIS is `gis_authoritative` (unless explicitly logged).
  `fs_missing_record` rows expose the SBIS values for keyed bungalows the FS lacks;
  `include_flag` rows cover matched include/status disagreements in both directions
  (GIS includes what SBIS excludes, and the reverse).

Still no write-back: the corrections are exported for the GIS team to apply in ArcGIS.
`apply_edits()` remains the deferred seam if SBIS ever pushes changes upstream directly.

**Field-map scope (open).** The comparison covers the 10-field general-data intersection
(name, as-built, cp_name, sub, mp_pre, mp_rr, section, size, ptc, xing_tracks). Adding a
field is a one-line `FieldSpec` and the export inherits it; whether the audit needs
bungalow `type` / track count / coordinates is pending the auditor's checklist vs. the live
layer-12 field list.

## Context

ArcGIS Enterprise (`rmigis`) is authoritative for railroad GIS assets — bungalows,
signals, crossings — exposed as feature services. The platform already uses ArcGIS
Portal **for identity only** ([identity/arcgis.py](../../platform/src/platform_core/identity/arcgis.py)
authenticates a user, then drops the token); it has never fetched feature *data*.
The core spec anticipates this: §3.3 lists "**ArcGIS sync jobs**" as a worker
workload and §6 notes Power Query already runs against ArcGIS feature services.

The need is broad, not SBIS-specific:

- **SBIS** wants the bungalow feature service to seed/refresh inventory. `bglw_id` is
  already marked "GIS-authoritative" ([models.py](../../modules/sbis/src/sbis/models.py));
  location/crossing/signal fields come from GIS, while equipment, units, status,
  `dax_review_status`, and notes are **SBIS-authored**.
- **TIVS and CVS** already fetch (and may write) ArcGIS data in their legacy apps;
  on migration they should reuse one platform capability, not carry three bespoke
  integrations forward.

This calls for a **platform-core** capability — a shared, tokened, audited client —
consumed by modules, mirroring the `storage/` precedent (Protocol contract +
settings-driven factory singleton + swappable backends).

## Decision

Build `platform_core/arcgis/` as a layered capability. Four shaping decisions
(confirmed 2026-06-06):

1. **Both data-flows from one client surface.** `query()` returns features for
   **live/proxy** reads *and* feeds a **sync-into-Postgres** engine (sync = query +
   field-scoped upsert). Sync is the primary flow for inventory (module DB stays the
   editing source of truth; ArcGIS is upstream reference); live/proxy covers
   occasional spatial/display reads.

2. **Pluggable token provider; app-login is the default.** An `ArcGISTokenProvider`
   protocol with two implementations:
   - `AppLoginTokenProvider` — OAuth2 **client_credentials** against a dedicated,
     least-privilege "data" app item, token cached and auto-refreshed. The only
     mode needed for background/worker sync. Credential lives in **Secrets Manager**
     alongside the SSO secret.
   - `UserTokenProvider` — SSO **token passthrough** for live, per-user
     permission-scoped reads. **Gated on a prerequisite**: the SSO flow must first
     persist + refresh the user's access/refresh token (encrypted), which it does
     not today. App-login lands first; user-passthrough is a fast-follow.

3. **Read-only now; write-back designed-for, not built.** Ship `query()` +
   `layer_info()` + sync. Reserve `apply_edits()` (add/update/delete) behind a
   permissioned, audited seam so it is additive when a module (likely TIVS/CVS)
   needs to push changes upstream — no refactor.

4. **Attributes + optional centroid; no PostGIS.** The client may *return* geometry,
   but persistence stores feature attributes plus a centroid as plain
   `latitude`/`longitude` numerics. Real geometry / spatial queries are a later ADR.

### Architecture

```text
platform_core/arcgis/
  contracts.py   Protocols + dataclasses: ArcGISTokenProvider, FeatureServiceClient,
                 Feature, LayerInfo, QuerySpec, EditResult
  token.py       AppLoginTokenProvider (client_credentials, cached/refreshed);
                 UserTokenProvider (passthrough) — later
  client.py      httpx FeatureServiceClient: query() with auto-pagination
                 (maxRecordCount / resultOffset / exceededTransferLimit),
                 layer_info(); apply_edits() reserved (write-back, later)
  config.py      FeatureSource (url, layer, auth mode, secret ref) — settings now,
                 admin/config registry later (spec config-registry alignment)
  factory.py     get_arcgis(source) -> configured client (singleton per source)
  sync.py        generic upsert engine: (client, QuerySpec, key, field-map,
                 owned-fields) -> upsert with provenance + an editDate watermark
                 + drift reporting
```

Modules declare *what* and *how to map*, never *how to talk to ArcGIS*. SBIS:
`sources.py` (field map, GIS-owned column set, key=`bglw_id`) + `sync_bungalows`
(merges into `sbis.bungalow`, **preserving SBIS-authored columns**) + an ARQ worker
task + an admin "Sync from GIS" button with a last-run/drift panel.

Cross-cutting, reusing existing machinery:

- **Field ownership** — sync overwrites only the GIS-owned column set; SBIS-authored
  columns and all child tables are never touched (the opposite of the one-way
  `importer`, which TRUNCATEs).
- **Provenance + watermark** — a `gis_sync_state` table (platform schema) keyed by
  (project, source): last run, editDate watermark (incremental pulls), row counts,
  and drift (in-DB-not-in-GIS / in-GIS-not-in-DB), surfaced to the admin status view.
- **Background jobs** — sync runs as ARQ tasks (the anticipated domain job; the
  worker currently has only `ping`), on-demand and scheduled.
- **Audited** — every sync run, and later every write-back, via the platform audit sink.
- **Project-scoped** — a source maps a project to a feature service / where-clause.

### Deferred

- `UserTokenProvider` (requires SSO token persistence + refresh).
- `apply_edits()` write-back (build when a module needs it).
- PostGIS / real geometry and any spatial-query surface.
- Promoting `FeatureSource` config from settings into the admin/config registry.

## Consequences

- One hardened, tokened, audited GIS client replaces three bespoke integrations on
  TIVS/CVS migration; the I/O unifies while module valuation/sync logic stays local.
- The worker gains its first real domain task; sync is incremental via the editDate
  watermark and idempotent via field-scoped upsert.
- Field ownership must be defined per synced table (which columns GIS owns). For
  `sbis.bungalow` the exact set is confirmed against the live feature-service field
  list, not guessed.
- App-login adds a second ArcGIS app registration (least-privilege, data-only) and a
  Secrets Manager entry; user-passthrough is intentionally not on the critical path.
