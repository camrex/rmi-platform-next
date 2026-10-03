---
status: open
kind: architecture
date: 2026-06-08
refs: []
source_status: "Proposed (2026-06-08)"
imported_from: rmi-platform/docs/adr/0008-bungalow-naming-convention.md
imported_on: 2026-10-03
---
# 0008 — Signal bungalow naming convention

**Status**: Proposed (2026-06-08)

## Context

`bglw_name` is free text and `sbis_curated` (SBIS owns it; see ADR 0007 reconcile
field map). A scan of the 154 named bungalows in the `26-150` inventory shows the
names are not arbitrary — they encode a recurring grammar — but the grammar is
applied inconsistently (mixed case, redundant suffixes, transposed mileposts, two
subdivisions using different sub-styles). The GIS-corrections audit needs a *canonical*
name to compare GIS `asset_name` against, and editors need names that are consistent
by construction rather than hand-typed.

The fix is to stop treating the name as a single free-text fact and instead **derive
the display name from structured fields**. Names then become consistent automatically,
the validator becomes a comparison against the generated form, and the audit can emit
the canonical name as the correction value.

## The five facts hidden in a name

A name today overloads five orthogonal facts. Each gets a home:

| Fact | Example | Field |
|---|---|---|
| Location anchor | milepost, subdivision | `mp_rr`, `sub` *(exist)* |
| Primary function | CP / INT / XING | `folder` (normalized) *(exists)* |
| Place name | KEDZIE, HAVEN RD | `cp_name` / `xing_name` *(exist)* |
| Designator | MAIN, EXT 2, BUNG 3, TOWER, HT | **`designator`** *(new)* |
| Equipment role | DAX, RPTR, ESL/SCC | role flags *(new or derived from equipment)* |

Most components already have columns. The only genuinely new field is `designator`.

## Decision

### 1. Function taxonomy — located vs. equipment-role

- **Located functions** define a named *place* and are mutually constrained:
  **CP, INT, XING**. CP and INT never co-occur; XING may ride along with either.
- **Equipment-role functions** describe *what the bungalow does* and are already
  captured by the detailed equipment inventory: **DAX, RPTR, ESL/SCC, AFTAC**.

### 2. Primary name = the located function

When a bungalow has a located function, that function names it. XING is the **only**
thing allowed in a secondary slot, because a grade crossing is a distinct named public
asset (DOT number + road), not just equipment.

### 3. Equipment roles are flags, never name text

Since the equipment is captured in detail, DAX / RPTR / ESL/SCC / AFTAC become
booleans (or are derived from `main_systems`/equipment), not name strings. This drops
the redundant `| DAX` / `| RPTR` secondaries and the `(GCP)`/`(HXP)`/`(AFTAC)` type
parentheticals from the name entirely.

### 4. Equipment-only bungalows — priority order

A bungalow with *no* located function still needs one role to lead its name. Priority,
most location-defining first: **ESL/SCC > DAX > RPTR**. (This makes
`ESL/SCC 9.15 | RPTR` correct as-is and reclassifies `RPTR 18.64 | DAX` → primary
`DAX 18.64` with an `rptr` flag.)

### 5. Drop "HOUSE"

Redundant — every bungalow is a house. The `designator` carries the distinction
(`CP KEDZIE BUNG 3`, not `CP KEDZIE - BUNG 3 HOUSE`).

### 6. New `designator` field — free text, soft-validated

Distinguishes co-located bungalows (up to 6 share one CP: KEDZIE=6, HALSTED/JB=4).
Stored as a **free-text** `String` column (flexibility for edge cases was preferred
over a hard enum). The UI offers a **suggested vocabulary** for autocomplete and the
validator flags off-vocabulary values as advisory, but neither is enforced:

> `MAIN`, `EXT`, `EXT 1`, `EXT 2`, `EXT 3`, `BUNG 1`, `BUNG 2`, `BUNG 3`, `BUNG A`,
> `TOWER`, `HT`, `AUX`, `2W`, `BRIDGE "x"`, `INTERFACE`, `RELAY`

## Canonical grammar

```text
<PRIMARY> [<DESIGNATOR>] [| XING <DOT#> <ROAD>]

CP:                 CP <PLACE> [<designator>]      e.g.  CP KEDZIE BUNG 3
INT:                INT <mp> [(circuits)]          e.g.  INT 16.36 (164/165)
XING:               XING <DOT#> <ROAD>             e.g.  XING 174021Y HAVEN RD
equipment-only:     <ROLE> <mp>                    e.g.  DAX 24.13
  (ROLE by priority ESL/SCC > DAX > RPTR)
secondary (only):   | XING <DOT#> <ROAD>           e.g.  INT 16.36 | XING 174001M 9TH AVE
```

- `<mp>` is `mp_rr` rounded to two decimals. Historical plan labels sometimes carry a
  rounded *plan* milepost that differs slightly; the generated name uses `mp_rr`. Large
  divergence (e.g. `INT 56.48` vs `mp_rr 26.515`) is a data-entry error the validator
  flags, not a second milepost to preserve.
- UPPERCASE; single spaces; straight quotes.

## Consequences

**Automation unlocked.** With the components structured, `bglw_name` is *generated*,
not typed. The validator is a diff of stored-name vs. generated-name; the GIS audit
emits the generated name as the `sbis_curated` correction value (extends the
corrections CSV from ADR 0007 amendment 2026-06-07c).

**Migration is a one-time backfill.** Parse the existing 154 names into the structured
fields (function ← `folder`; place ← CP/road; designator ← the `- … HOUSE` suffix;
role flags ← `|` tokens and `( )` types), regenerate canonical names, and report
anomalies for review. Known anomalies surfaced by the scan: `INT 56.48` (transposed
milepost), `WRONG PLAN` (placeholder), `Bridge "R"` (missing prefix + casing),
KENOSHA `INT nn.nn House` (mixed-case/zero-pad outliers).

**Two subdivisions to reconcile.** GENEVA/HARVARD use the UPPER, no-suffix style;
KENOSHA uses mixed-case `House` suffixes and zero-padded mileposts. The backfill
normalizes both to the canonical form.

## Implementation — the Reconcile page

The convention is delivered through the existing GIS reconcile machinery (ADR 0007
Slice 2b, branch `feat/sbis-gis-corrections-audit`), not a parallel UI. The generated
name is computed from the bungalow's *own* SBIS fields, so it is a **third axis** on the
name cell — an SBIS-internal consistency check — alongside the SBIS-vs-GIS comparison.

- **`naming.py` (pure)** — `generate(row) -> str` and `validate(row)`, tested against the
  real inventory names. Runs off existing columns first; `designator` slots in once added.
- **`designator` column** — one alembic migration in `modules/sbis` (mirrors the
  `gis_field_ack` migration on the same branch).
- **`Cell` gains `convention` + `convention_differs`**, populated only for `bglw_name` in
  `compare_fields()`. The name cell renders **S / G / C** and, when SBIS ≠ convention,
  a **`← Conv`** button beside `← GIS`.
- **Apply route** — `POST /sbis/reconcile/apply-convention/{bglw_id}` sets
  `bglw_name = generate(b)`, audited, single-row re-render — a direct clone of the
  existing `reconcile_apply`.
- **Convention → GIS rides the existing corrections CSV.** `bglw_name` is `sbis_curated`,
  so once SBIS holds the convention name and it differs from GIS, the current
  `gis_corrections_csv_rows` `field` row carries it. The GIS team joins the CSV on
  `bglw_id` and field-calculates the new name in ArcGIS. No write-back, no new CSV column.
  (The join column is named `asset_id` since the 2026-09-17 amendment below.)

**Coverage (accepted limitation).** The reconcile page only shows bungalows keyed to a
GIS match, so names on unlinked / GIS-unmatched bungalows aren't surfaced *here*.
The convention check is SBIS-internal and could later back a standalone naming view to
close that gap; deferred — start on the reconcile page.

## Open / deferred

- **INT circuit numbers** (`(164/165)`): kept in the grammar as optional, free-form
  annotation for now — not parsed, validated, or enforced. The eventual path is to
  connect to the **signal feature service**: the signals associated with a bungalow
  carry these numbers, so they could be sourced and enforced from there rather than
  hand-kept in the name. Deferred to that integration (another day).
- **Role flags vs. derivation**: whether DAX/RPTR/ESL-SCC become explicit boolean
  columns or are derived from `main_systems`/equipment is an implementation choice; the
  convention only requires they leave the name string.
- **AFTAC**: currently appears as both a `folder` and a DAX `type`. Treated here as an
  equipment role (flag), consistent with the others.

## Amendment 2026-06-09 — field-driven generation + configurable templates

The original `generate()` derived the name by *parsing the stored `bglw_name`*, so a
bungalow with **no name** got nothing — even when its structured columns held everything
needed. That contradicted the decision above ("derive the display name from structured
fields"). Two changes close the gap:

1. **`generate()` is now field-driven.** `folder` (a controlled vocabulary —
   `CP/INT/XING/DAX/RPTR/SCC_ESL/INT_XING/CP_XING/MISC`) classifies the function, and the
   structured columns supply the slots: place ← `cp_name`, crossing ← `xing_dot_num` +
   `xing_name`, milepost ← `mp_rr`, plus `designator`. The legacy name is parsed only as a
   *fallback* for a component no column populates. A nameless bungalow now gets a name on
   the Reconcile page, and the two empty-name guards (in `compare_fields` and the
   apply-convention route) are gone.

2. **The format is a per-project setting, not hardcoded.** Each function renders from a
   template (e.g. `CP {place}[ {designator}]`); an optional `[ … ]` group drops with its
   field so separators vanish cleanly. Code defaults reproduce the dash-free canonical form;
   a project may override any template (e.g. a `" - "` separator) via a `naming_format` row
   in `sbis_setting`, edited on the Settings page. Stored templates self-heal (blank,
   malformed, or unknown keys fall back to the default), matching the order settings.

This narrows the earlier *Coverage* limitation: nameless **matched** bungalows are now
covered; unlinked / GIS-unmatched ones still await the standalone naming view.

## Amendment 2026-06-09b — the name milepost is `mp_plan`, not `mp_rr`

The canonical grammar above said `<mp>` is `mp_rr` (the precise railroad milepost). In
practice the milepost people recognize is the **plan** milepost embedded in the as-built
name (e.g. `GENEVA_05.65` → `5.65`), which differs slightly from `mp_rr` (e.g. a Geneva
intermediate plan `4.67` vs `mp_rr 4.616`). Using `mp_rr` produced names (`4.62`) that
didn't match the as-built world.

**Decision:** the generated name uses a dedicated **`mp_plan`** column.
`generate()` prefers `mp_plan`, falling back to `mp_rr`, then to whatever the legacy name
parsed. `mp_rr` remains the precise locational value (reconcile / GIS / measured-MP).

- `mp_plan` is **auto-derived** from the as-built/plan name (`naming.mp_from_plan_name`) and
  backfilled by migration; it is **editable** on the bungalow page.
- **Shared plans** (one as-built covering several bungalows) backfill the *same* `mp_plan`
  for each — those are flagged for manual correction (surfacing TBD; the field is editable
  in the meantime).
- The `milepost_mismatch` validator is unchanged: its tolerance (`1.0`) already accepts the
  small plan-vs-`mp_rr` gap while still catching wild/transposed-digit typos.

Supersedes the `<mp> = mp_rr` note in *Canonical grammar*.

## Amendment 2026-06-09c — accepting a manual name (#23)

The generated name is a *suggestion*, not a mandate. Some names are deliberately
non-canonical (a hand-shortened name to fit the GIS `asset_name` length, or a legitimate
exception). A `bungalow.name_locked` flag marks such a name as **accepted**: while set, the
Reconcile page stops offering `← Conv` for it and drops the name-too-long warning. An editor
toggles it from the name cell (`✓ accept` / `↺ unlock`), audited; the convention is still
computed (for display), it's just no longer flagged as differing. Default off, so existing
behavior is unchanged.

## Amendment 2026-06-09d — shared-plan `mp_plan` flag (#43)

When one as-built **plan covers several bungalows**, they all backfill the *same* `mp_plan`
(the value parsed from the shared plan name), but their real mileposts differ. The bungalow
**edit page** now warns on the Location card — *"Shared plan: N bungalows share this as-built…
set each one's MP (plan) to its own milepost"* — driven by the pure `naming.shared_plan_info`
over the sharing bungalows' `mp_plan` values. The warning is informational and **clears once
every sharing bungalow has a distinct, non-null `mp_plan`** (i.e. each has been corrected).

## Amendment 2026-09-17 — the corrections CSV is joined on `asset_id` (#1910)

Owner ruling 2026-09-17. The join column named above in *Convention → GIS rides the
existing corrections CSV* is **`asset_id`**, not `bglw_id`: the GIS team joins
`/sbis/reconcile-corrections.csv` (and its per-field workbook) on `asset_id` and
field-calculates from there. Only the column NAME changes — the value is the same asset
id it always was, and blank where GIS resolves none.

Why: `bglw_id` was the name of `sbis.bungalow.bglw_id`, the stored copy of the asset id
that **#1472 dropped**; the id is now resolved from the synced GIS row, whose attribute
is `asset_id`. The SBIS JSON API took that name in v1.54.0 (#1473) and the xlsx
inventory export in #1910, each with no deprecation window, so the corrections
deliverable was the last surface calling one value by two names. **No deprecation
window here either**: a saved ArcGIS join or query reading `bglw_id` must be repointed
to `asset_id`.

Supersedes the `bglw_id` join key in *Implementation — the Reconcile page*. See also
ADR 0007's amendment of the same date, which records the change in the ADR that defines
the corrections deliverable.
