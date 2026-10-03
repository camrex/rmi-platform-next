---
status: ruled
kind: architecture
date: 2026-07-28
refs: []
source_status: "Accepted (2026-07-28) · **Refines**: ADR 0007 (see its 2026-07-23"
imported_from: rmi-platform/docs/adr/0016-gis-data-access-posture.md
imported_on: 2026-10-03
---
# 0016 — GIS data access: broad reads, narrow writes

**Status**: Accepted (2026-07-28) · **Refines**: ADR 0007 (see its 2026-07-23
amendment pointer) · **Mechanism**: [ADR 0023](0023-gis-ingestion-contract.md)
states the ingestion contract this posture assumes (who fetches, cadence,
refusal semantics, sync control, identity) · **Informed by**: the #408 access
audit; owner decisions on #407 and #9.

## Context

The #408 audit (2026-07-23) found the storage layer already module-agnostic —
dataset bindings and platform-synced rows (`platform.gis_dataset_row`) are keyed by
project + dataset with no module in the key — while the de-facto read gate is
manifest slot declaration. It also found the same physical layers fetched twice
(platform dataset sync and TIVS/CVS typed syncs), including platform copies no
surface reads. Meanwhile the concrete needs are cross-module: SBIS showing
related-asset info from a bungalow, CIV's sidebar displaying asset (eventually
property) data.

## Decision

1. **Reads are broad.** Every project-bound dataset is readable by every module
   enabled on that project. The platform-synced rows
   (`platform_core.arcgis.synced`) are the blessed cross-module read API; slot
   declaration remains the *binding/sync consumption* declaration but is
   **not** a read gate (refines ADR 0007 #141's "slots declare consumption").
   Capability is always computed at runtime from the (project, enabled
   modules, bound datasets) triple — never assumed from the global registry:
   projects run mixed module sets (CVS-only, TIVS+SBIS+CIV, CIV-only, …) and
   nothing may presume a module is present. Broad reads are module-level
   posture, not a user bypass: every read still runs behind the platform's
   access checks (project membership + the user's module access) — the
   DB-first path relaxes which MODULE may read a dataset, never which USER.
2. **DB-first.** Storage is cheap; Portal traffic is the scarce resource.
   Module surfaces read synced attributes; live Feature Service calls are
   reserved for maps (client-side, ADR 0015), single-feature apply paths, and
   background syncs — plus one named, bounded exception, server-side raster
   export for generated documents (see the 2026-09-11 amendment below). The
   target sync architecture is **one Portal fetch per
   layer per cycle** (#451, with #9's watermark sync-in as the candidate
   engine) — refining ADR 0007 #142's "TIVS keeps its own typed sync" and
   reconciling 0007's original watermark intent with the shipped full-refresh.
   The platform sync is standalone and complete by itself; module typed
   derivations are **optional subscribers** that run only where the module is
   enabled — the sync never depends on any module's presence, and a dataset
   with no current subscriber is legitimately synced (availability ahead of
   subscription), not an error.
3. **Two data classes, by origin — guidance, not prohibition, on the second.**
   *GIS-origin* data (attributes synced from the Portal) is project data,
   shared by default per §1. *Platform-origin* data exists only in
   RMI-Platform and is module-owned: most explicitly SBIS's contents-based
   inventory, TIVS's cost/valuation data, and CVS's rates, unit values, and
   valuation (CVS may later expand to sales and analysis, but today those are
   what live only here). Cross-module access to platform-origin data is a
   likely and legitimate want — e.g. CIV surfacing SBIS data — and is crossed
   via deliberate seams (the ADR 0010 SBIS→TIVS bungalow seam is the working
   precedent). A design bar, not a ban. Seams are **optional capabilities,
   never hard dependencies**: a consumer renders by data availability (SBIS
   absent → less data, never a failure), so module enablement never becomes
   viral — TIVS runs without SBIS on a no-bungalow project today, and that
   discipline is the rule for every future seam.
   **A third class exists since 2026-09-30**
   ([ADR 0025](0025-third-party-evidence-reconciles-against-the-inventory.md)):
   *third-party evidence*, a statement received from outside about the same
   assets, as of a date, held beside the owning module's inventory and never
   written into it.
4. **Writes are narrow — Deliberate and Guarded.** Write-back (`apply_edits`,
   #9) is never a capability that comes free with GIS access. It is granted
   per module (allow-list — not all modules get it), per project (opt-in),
   governed by the field-ownership map (what may flow back), dry-run-first,
   and audited. This tightens ADR 0007's deferral ("build when a module needs
   it"). The likely first implementation is **SBIS**, where the groundwork
   exists: attributes are already marked for update in SBIS, then exported and
   manually joined in the GIS — write-back automates that last leg. Beyond the
   module allow-list, write-back is expected to be a **user-explicit
   permission**: being an editor does not itself confer the right to write
   back to GIS. The permission model's shape is deliberately NOT designed here
   — user permissions are their own future topic; this records only that
   write-back must not be assumed from editor role.
5. **Bindings declare availability; modules subscribe.** An admin binds — at
   their discretion, at setup or later — the datasets that exist for the
   project (a TIVS project has track asset layers, a CVS project segments, a
   CIV project OID imagery); binding is never automatic. Modules (or module
   modes — the #437 CIV-only viewer may subscribe to less than full CIV, so
   the consumer key must not hard-code module identity) **subscribe** to what
   they consume. Each module names its **required** subscriptions — CIV: OID;
   SBIS: bungalows; CVS: subject_segments; TIVS: per-process datasets, where a
   missing dataset disables that process, not the module — surfaced as
   readiness ("enabled but not ready: X not available"), never a hard
   enable-time failure. Subscriptions plus module identity on reads make
   consumption observable, closing the loop the #408 audit had to answer by
   code sweep: the admin lifecycle is **bind (discretionary) → observe
   (automatic) → curate** ("nothing reads this — drop it" — a judgment that
   must rest on OBSERVED usage, not declarations alone; until tracking
   exists the UI presents unbind as judgment, never as "safe"), and the same
   substrate (subscriptions, read recency, sync runs) yields in-platform
   usage metrics with no external telemetry stack.

## Amendment (2026-09-11): server-side raster export is the one named exception

§2 reserves live Feature Service calls for client-side maps, single-feature
apply paths and background syncs. One shipped path is none of those:
**server-side raster export for generated documents**. It stays, deliberately,
and is bounded here so it cannot grow into an attribute path (#1413, the #408
re-audit's finding 9).

- **What it may fetch — an image, never data.** A rendered picture of a bound
  layer over a caller-supplied extent: today the layer's MapServer twin
  `export`, pinned to the bound layer (`layers=show:<id>`), returned as PNG.
  Never features, attributes, or a query. The basemap-composited refinement
  ADR 0012 mentions (the org's `Export Web Map` task) is the same class — an
  image for a document — and falls under this exception when it lands.
- **Why DB-first does not reach it.** §2 exists because synced rows can answer
  an attribute question without Portal. They cannot draw a map: they carry no
  symbology, and a generated PDF runs no JavaScript, so the client-side map
  path is not available either (ADR 0012, "no JS in PDFs, by construction").
  The image has to come from the server: one export per generated sheet — the
  exhibit batch renders a PDF per asset and requests one image for each.
- **How it stays inside the GIS rules.** The layer resolves through the
  project's binding (`resolve_layer_url`), the token is the platform's
  server-side app token, and the module never handles a URL or a token —
  `platform_core.arcgis.export.export_map_image` takes a slot and an extent.
- **How it fails.** A failed export degrades to a placeholder in the document,
  with a warning — never a dead batch, never a silent drop (ADR 0012's slice-D
  rule).
- **Who calls it.** The TIVS exhibit-sheet task (`tivs.reports.tasks`, the sheet
  map insets), and the project home's map (widened below, 2026-09-14; #1780). A
  new caller conforms if it fetches an image within
  the bounds above. Anything that reads attributes live instead is drift from §2,
  not a further instance of this exception.
- **What it does NOT cover — the caller's own live read.** Before exporting,
  that task makes a separate live **feature** read: `_asset_points` queries the
  bound layer for `asset_id` and point geometry to centre each inset. That read
  is not raster export and this exception does not reach it. It is the
  exhibit task's geometry need that ADR 0023 routes to #1042 ("the one live
  read with a real obstacle, not inertia": enforced lat/long on point assets,
  so the centre can come from synced rows), and it remains a named departure
  from §2 until #1042 lands.

### Widened (2026-09-14): a bound web map, for the project home

The owner ruled that the project's map is a **static image of a bound Portal web map**,
not a live map (#1724). The same day, before it reached production, it moved from the
TIVS dashboard to the **project home** (#1780), because a project map is not one
module's. That is the Export Web Map class named above, and a page rather than a
generated document, so the exception is widened to it on these terms:

- **What it fetches is still an image.** `platform_core.arcgis.export.export_web_map`
  takes a `(module, slot)` web-map binding and an extent, and returns one PNG with the
  layers it drew. The home's map binds under the platform's own key, `("project",
  "home")`, which no module gates.
- **What it reads to build that image is the web map item, never data.**
  - `portals/self` supplies the print service the portal advertises
    (`helperServices.printTask`).
  - The bound item's `/data` supplies the map's layer list, its basemap and each
    layer's own definition, which is configuration.
  - The item itself is read only for its saved extent, when the project has nothing
    placeable to frame the map from.
  - No feature, attribute or query is read. The layers are drawn by the print
    service, not by the platform.
- **What frames it is the synced rows, DB-first (§2).** The box is drawn over the
  `lat`/`long` already landed for the project's bound, in-scope datasets
  (`platform_core.arcgis.synced.placed_boxes`). No live query sizes the map.
- **How it stays inside the GIS rules.** Same as the layer export:
  - The map resolves through the project's binding.
  - The token is the platform's server-side app token.
  - The module never handles a URL or a token.
  - The token is sent only to the portal and the print service, and only over https. The
    output file is fetched only from an https URL on one of their own hosts, and anything
    else is refused before a request is made.
  - What comes back must be a PNG, by its content type and its signature. The project
    home serves those bytes from the platform's own origin, so an SVG or anything else is
    refused rather than passed on.
- **How it fails.** The project home renders a stated placeholder when nothing is bound,
  storage fails or the export fails, never a broken image. The image never sits in first
  paint.
- **How often Portal is asked.** One export per picture, cached per project under a name
  that changes with the binding, the extent, the latest sync and the UTC day. An edit
  made inside Portal to the map therefore shows within a day, without a Portal read on
  every page load. First views of the same picture arriving together on one node share
  one export.
- **Who calls it.** The project home's map (`platform_web.project_map`, #1780). It also
  reads which drawn layers filter to included records, from the item's own layer
  definitions, so the page can say whether excluded records may show.
- **Proven live** on 2026-09-14 against 26-150's map: 14 layers plus imagery, returned
  as an 882 KB PNG at 800×500.

## Durability note

GIS data and RMI-Platform data back up on independent timelines (the Portal
has its own regime), so **sync provenance is part of the durable record**:
when each row/run synced, from what schema, under which run — retained, never
pruned as noise — so any future restore can state what GIS state a platform
state was built against. Backup/restore itself (disaster recovery vs
project-archive close-out, restore-context metadata, per-release image
custody) is designed separately; this ADR only obligates the record.

**Amended 2026-09-16 (#1499).** "Never pruned" now means *never pruned by the
application*. Sync runs and their gap rows accumulate every day, so the owner
ruled that a **platform admin may choose sync runs to delete** (Admin → Sync
history, `/admin/sync-history`) across the three GIS sync-run tables
(`platform.gis_dataset_sync_run`, `tivs.tivs_sync_run`, `cvs.cvs_sync_run`).
There is no retention window and no scheduled job. A run's gap rows go with it
and never otherwise. A run anything still stands on cannot be deleted: the
latest succeeded run of its dataset or source (by completion time *and* by run
number), a run whose landing rows are still on the table, a platform run a TIVS
or CVS derivation names, a run a spent empty-landing grant names, and a TIVS run
a valuation snapshot's data basis names. The delete re-checks all of that under
the syncs' own locks and refuses the whole selection if any run is protected.
Every deletion is audited (`platform.sync_history.runs_deleted`) in the same
transaction. The record this section obligates is therefore kept for everything
a current landing, derivation or snapshot stands on; older history is removed
only as a deliberate, audited act of a person.

## Non-decisions (delegated)

The mechanisms stay open for design on their issues: the read/subscription
API, enforcement shape, and consumption tracking (#450); sync consolidation
under the optional-subscriber constraint (#451); SBIS request-time coupling
(#452); CIV sidebar + `oid` promotion (#453); watermark sync-in and write-back
mechanics (#9); backup/restore, the permissions model, and the metrics
surface (their own tracking issues). No implementation precedes agreement.

## Consequences

- Cross-module features (SBIS related assets, CIV sidebar) need no new
  bindings or plumbing — they read the project's synced rows.
- The slot model's meaning narrows toward subscriptions; docs and reviews
  should stop treating slot declaration as an access boundary.
- ADR 0007 clauses this refines carry inline pointers here, so the two
  documents cannot silently diverge.
- Write-back designs are reviewable against four explicit gates: what (field
  ownership), which module (allow-list), which project (opt-in), which user
  (explicit permission, model TBD) — with dry-run-first and audit underneath.
- Every surface moved from live Portal calls to synced rows also works inside
  an offline restore — the access posture and the durability story are the
  same investment seen from two angles.
