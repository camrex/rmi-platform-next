---
status: ruled
kind: architecture
date: 2026-08-07
refs: []
source_status: "Accepted (2026-08-07) · **Source**: the 2026-08-06 platform review"
imported_from: rmi-platform/docs/adr/0020-shared-web-kit-and-enforced-promotion.md
imported_on: 2026-10-03
---
# 0020 — Shared web kit: platform-owned page shell, vocabularies, and islands; sweep-tested against re-copying

**Status**: Accepted (2026-08-07) · **Source**: the 2026-08-06 platform review
(`docs/reviews/PLATFORM_REVIEW_2026-08-06.md`)

## Context

The 2026-08-06 whole-repo review found that the web layer's shared grammar is
held together by convention alone, and the convention has stopped holding.
Every module re-implements the page shell; the Pico/HTMX CDN pins **and their
SRI hashes** exist in six copies; PM and CVS re-declared the kv-card CSS with
drifted metrics; the `.tag` chip family is forked between two layouts; and
three JS islands are byte-identical triplets while a fourth pair (the Tabulator
grids) has already diverged *behaviorally* — CVS carries an out-of-order
response guard that TIVS lacks. The same drift produced two security
asymmetries: a CSV-injection guard present in TIVS/CVS but absent from SBIS's
exports, and a path-traversal guard applied to the CVS parity fixture store but
not its byte-identical TIVS twin.

The standards already say *rule of three: the third copy gets promoted* — but
nothing detects a third copy, so promotion happens only when someone notices.
Meanwhile the one place we DO enforce a web-layer rule mechanically (the #472
inline-JS syntax gate, born from the v1.6.5 incident where one SyntaxError
blanked every TIVS grid) has proven the model: a sweep test that walks the
tree and fails on violations catches drift at PR time, not in prod.

## Decision

1. **`platform_core.web` owns the web kit.** Concretely, the kit grows to
   include (promoted incrementally, not big-bang):
   - the **document shell** — one `page_shell()`/`document()` owning the
     `<head>` assembly, the vendored/CDN asset pins **and SRI hashes**, the
     HTMX config meta, and the CSRF `hx-headers` body attribute;
   - the **status vocabulary** — tags/chips (`tag()` + `TAG_CSS`), warn/error
     banners, the `Notice` grammar it already owns, and a `status_region()`
     live-region helper so `role="status"` cannot be forgotten. *Delivered
     2026-09-04 (#1578) as `platform_core.web.vocab` — `VOCAB_CSS`, `tag()`,
     `banner()`, `field_error()`, `status_line()`, `when()`/`day()` — drawn
     from a **token layer** this ADR did not foresee, `platform_core.web.tokens`:
     every colour, density and chip-shape value declared once, Pico wearing the
     brand through its own variables, no build step (owner ruling, option B).
     The chrome's fixed actions are **icons** from the same kit —
     `platform_core.web.icons` (#775, 2026-09-08): inline SVG in
     `currentColor`, vendored not fetched, each link carrying its name as
     `aria-label` and `title`; bar 1's five, and a module's Settings as a
     gear in bar 3's slot, because settings are a module's, not the app's;*
   - the **shared islands** — browser-token mint, photo pane, ArcGIS map
     embed, the Tabulator grid island core, and the CSV export guard — each
     parameterized by config, never copied. *The Power Query token mint
     became the kit's served `connect.js` (#837, 2026-09-16) —
     `platform_core.web.connect`: `mint_token_controls(module_key, project)`
     puts the module key on the button, one delegated script serves the CVS,
     SBIS and TIVS connect pages; the photo pane is `platform_core.web.photos`.
     The map embed and the grid core are still per module;*
   - the **sync-run spine** — `SyncRun`/`SyncGap` model mixin, the gap
     truncation writer, and the run-report renderer;
   - the **xlsx kit** — media type, style palette, `cell_text`,
     `export_filename`, hardened sheet-title.
2. **Modules import; they never re-declare.** A module layout may *extend*
   the kit (module-local classes, extra CSS) but must not restate a shared
   selector, pin, hash, or island. Genuine deltas become parameters or
   documented overrides, not forks.
3. **Sweeps enforce it.** Each promoted piece lands with a repo-walking test
   in the style of `test_inline_js.py`: no module STYLE contains
   `article.kv-card` or a CDN pin; no `Markup(f"...")`-generated JS outside
   the gate; every inline island string (any quoting form, all src roots
   including `platform/src`) passes `node --check`. The sweep is the
   decision's teeth — a promotion without its sweep is not done. Concretely:
   shell/pins/vocabulary → the kit-import sweep (#836); islands → the #472
   gate extensions (#837); xlsx kit + sync-run spine → an import-only sweep
   (no module re-declares a writer) filed with #838. Each arrives in the PR
   that promotes its component, never later.
4. **Client config crosses as data, not code.** Island configuration ships in
   `<script type="application/json">` + `JSON.parse` (the pattern the grids
   already use), never as f-string-generated JavaScript. Islands above a
   trivial size are served as real static assets (the vendored-Tabulator
   precedent) so they are lintable and cacheable.
   *Delivered 2026-09-16 (#837): `platform_core.web.json_island(id, data)`
   renders the island (through `safe_json`) and the script `JSON.parse`s it
   by id; the seven `window.X = {json};` blobs (SBIS map, bungalow map,
   program map, project stamp; TIVS map, asset map, layout editor) are gone,
   and `test_inline_js.py` refuses a formatted `Markup()` or a
   `window.X =` f-string anywhere under a src root.*

## Consequences

- A CDN/SRI bump, a confirm-phrase change, or an island fix is a one-file
  change again; behavioral guards (grid `seq`, CSV injection) exist exactly
  once, so a fix cannot land on one twin and miss the other.
- New modules start from the kit and inherit the vocabulary — the "replicate
  SBIS" instruction stops meaning "copy SBIS's layout file".
- The rule-of-three standard keeps its judgment for *domain* code; for the
  web kit specifically, the threshold is stricter: the shell, pins,
  vocabularies, and islands live in the kit even at two consumers, because
  their failure modes (SRI mismatch, missing guard) are silent.
- Cost: promotions touch many files and need the same-PR doc updates the
  standards already require; sweeps add CI time (small — they are tree walks).
- Supersedes nothing; extends ADR 0004 (frontend) and ADR 0011 (grids), and
  gives #143 (design system) its foundation layer.
