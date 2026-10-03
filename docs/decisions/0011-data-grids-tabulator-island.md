---
status: ruled
kind: architecture
date: 2026-07-03
refs: []
source_status: "Accepted (2026-07-03)"
imported_from: rmi-platform/docs/adr/0011-data-grids-tabulator-island.md
imported_on: 2026-10-03
---
# 0011 — Data grids: vendored Tabulator islands over metadata-derived specs

**Status**: Accepted (2026-07-03)

## Context

TIVS needs config-driven data grids across 13 asset types — read-only inventory views in Wave 1,
a dense editable cost editor in Wave 2 ([plan](../planning/TIVS_2_0_PLAN.md) §3.1 risk #2,
issue #140). Dense editable grids are the known weak spot of the platform's server-rendered +
HTMX frontend (ADR 0004), so the approach had to be decided before Wave 2 commits to it.

The spike built the same metadata-driven grid twice against real synced data
(project 25-320 `track_cl_inv`: **1,982 rows × 70 columns**, ~139k cells):

- **Variant A — pure htpy/HTMX** (the SBIS `grid.py` pattern generalized): server renders the
  whole table; sort/filter are HTMX fragment swaps; inline edit uses SBIS-style per-cell
  live-save inputs.
- **Variant B — vendored JS grid island** (CIV-island style): server renders chrome + a mount
  div and a column config derived from the same spec; [Tabulator](https://tabulator.info)
   6.5.2 (MIT, single vendored dist file, no build step, no CDN) owns sort/filter/CSV/editing
  client-side with a virtual DOM.

Both variants rendered from one shared metadata layer: `tivs.grid.spec` derives a `GridSpec`
from the inventory `SourceContract`, so a new synced source gets a grid from its contract alone.
That layer is the durable piece; the question was only who renders it.

### Measurements (headless Edge via Playwright, local Docker stack)

| Metric | A: pure htpy/HTMX | B: Tabulator island |
| --- | --- | --- |
| Initial transfer | 3.55 MB HTML | 12.7 KB HTML + 2.8 MB JSON + 446 KB JS (cacheable) |
| Server render (TTFB) | 859 ms | 9 ms (page); 137 ms (data JSON) |
| DOMContentLoaded | 3.35 s | 0.23 s |
| Grid usable | ~4.8 s | ~1.0 s (Tabulator `tableBuilt`) |
| DOM nodes | 144,865 | 6,311 (virtual DOM) |
| Sort (one click) | 1,862 ms — full 3.5 MB fragment re-ship + re-parse | 280 ms, client-side, no network |
| Filter | 1,223 ms (server round trip incl. 300 ms debounce) | ~12 ms per header-filter keystroke |
| Inline edit round trip | 436 ms | 79 ms |
| CSV export | 102–159 ms server-side (565 KB) | 85 ms client-side (server CSV also kept) |

Mitigations for A were considered and don't change the outcome: gzip (not currently in the
middleware stack) would cut the transfer ~10×, but parse/layout of ~145k DOM nodes dominates
the 3.3 s DOMContentLoaded and the ~1.9 s per sort click; pagination fixes payload but breaks
the whole-frame scan/filter workflow appraisers actually have (and the cost editor makes it
worse — variant A renders ~4k live form inputs for just two editable columns of 2k rows).

## Decision

1. **Dense grid surfaces render as a Tabulator island**: server-rendered chrome + a mount div,
   a column config derived server-side from the `GridSpec`, data via a project-scoped JSON
   endpoint, Tabulator client-side for sort/filter/scroll/CSV and (Wave 2) cell editing.
2. **Tabulator over AG Grid Community.** Both are MIT single-file dists, but AG Grid gates the
   features a cost editor grows into (set filters, range selection/clipboard, Excel export)
   behind its commercial Enterprise tier — a predictable upsell cliff. Tabulator ships header
   filters, editors, clipboard, keyboard navigation, and CSV/XLSX download under MIT, in a
   ~475 KB vendored footprint (vs ~1 MB+).
3. **The dist is vendored** (`modules/tivs/src/tivs/web/static/vendor/`), pinned and served by
   the module — no CDN dependency for a core workflow surface, no build step, no npm graph.
   Upgrades are a reviewed one-file swap.
4. **htpy/HTMX remains the default for everything else** (ADR 0004 stands): page chrome,
   navigation, forms, detail panes, and small read tables. The island is a scoped exception
   for the same reason the CIV viewer and ArcGIS maps are: client-heavy interaction density.

### Containment rules (the anti-Streamlit clause)

The legacy app decayed by letting the UI framework own application logic. The island must not
grow the same way:

- **The server owns data, access, and audit.** Every row crosses the wire through a
  module-access-gated endpoint; the island never talks to anything but the module's own routes.
- **Grid structure is typed Python.** Column configs are derived from the `GridSpec` (itself
  derived from the `SourceContract`) and serialized to the island — never hand-authored in JS.
  A grid change is a Python diff, reviewable like any other.
- **Island JS stays presentation-only.** Sorting, filtering, scrolling, cell-edit UX — nothing
  else. Any value that matters lands via a normal platform POST (CSRF, RBAC, audit-in-
  transaction) and the server's answer is authoritative; Wave 2 edit flows follow the SBIS
  field-registry model server-side.
- **One vendored library, pinned.** No plugins-of-plugins, no second grid library, no build
  tooling. If a need exceeds Tabulator's MIT surface, that's a platform design discussion, not
  an npm install.
- **Server CSV stays.** Exports used for deliverables/parity come from the server path
  (`rows_to_csv` over the same shaped rows), not from whatever the client currently displays.

## Consequences

- Wave 1 inventory views and the Wave 2 cost editor build on one skeleton:
  `/tivs/grid/{source}` (page, `data.json`, `.csv`) rendering any registered inventory source
  from its contract. Editing arrives in Wave 2 as per-cell POSTs to typed endpoints.
- Accessibility: a plain `<table>` is natively screen-reader-friendly; Tabulator emits ARIA
  grid roles and (unlike variant A) real keyboard cell navigation, but it is a div-grid.
  Mitigation: the server CSV is always available, and read surfaces that don't need grid
  density should stay plain htpy tables per rule 4.
- ~475 KB of vendored, pinned third-party code enters the repo, served with cache headers.
  Security/update cadence is ours to watch (single upstream file, MIT).
  **Amended 2026-07-22 (#388):** the dist first shipped inside TIVS and was served from
  `/tivs/vendor/{filename}`. Once CVS needed the same library for its reference grids
  (#375), a per-module copy would have meant several pinned copies drifting apart on a
  security update — the hazard "one vendored library, pinned" exists to prevent. The dist
  now lives once in `platform-web/src/platform_web/static/vendor/` and is served at
  `/vendor/{filename}`; every grid-mounting module links that URL. Modules still don't
  import the composition root — the coupling is a URL string, exactly like the Pico
  stylesheet they already reference — so a project with CVS but not TIVS still gets
  working grids.
- The spike measured ~2k rows; Tabulator's virtual DOM + optional progressive/remote modes
  give headroom for the larger frames (10k+ segments) bigger projects will bring, where
  variant A's full-table render is already past its ceiling at 2k.
- The htpy/HTMX variant and the per-cell edit-echo measurement rig live in the spike branch
  history (PR for #140), not in `main`.
