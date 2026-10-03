---
status: ruled
kind: architecture
date: 2026-08-04
refs: []
source_status: "Accepted (2026-08-04, owner-approved in session) · **Relates to**: ADR 0009"
imported_from: rmi-platform/docs/adr/0018-structure-component-decomposition.md
imported_on: 2026-10-03
---
# 0018 — Signal and crossing structures decompose into priced components

**Status**: Accepted (2026-08-04, owner-approved in session) · **Relates to**: ADR 0009
(code-owned calcs), ADR 0010 (SBIS source of record) · **Supersedes**: the #654 epic's
decisions 3 and 4 (whole-configuration structure identities with length banding) and the
Wave-4 whole-string crossing classes · **Feeds**: the structure-components epic

## Context

The #654 epic made SBIS the signal-equipment inventory + costing home for turnouts,
derails, signal structures, and crossings. Turnouts/derails price naturally: injection
lands **component** lines (machine, ESL, SCC, heater) on the asset and each component is
priced once in the external catalog. Structures and crossings shipped differently:

- **Signal structures** (decisions 3+4): one catalog item per whole identity — structure
  type + normalized head config + detail, with an optional length *band* for
  bridges/cantilevers (`StructureSpec`). Every distinct configuration needs its own
  hand-created item and its own price; ambiguous or uncovered lengths queue.
- **Crossings** (Wave 4): each pipe-delimited `equip_summary` part is a catalog identity
  *verbatim* (`display_name = "C1L-2F-1B"`). Every distinct configuration string is an
  item needing a price.

The operational pass exposed the cost of that shape: 26-150 alone queued **~97 distinct
structure identities** awaiting an engineer banding pass, and every new configuration
mints another identity forever. Meanwhile the engineers' actual pricing knowledge is
per-*component*: what a 3-aspect colorlight head costs, what a mast costs, what a bridge
costs at a base length plus so much per additional foot.

Prod vocabulary (pulled from synced rows, 2026-08-04) confirms the shape:

- Structure types: `MAST` (507), `BRDG` (92, lengths 0–130 ft), `DWARF` (92), `CANT`
  (9, 36–84 ft), `MASTB`, `BRPST`, `OTHER`, blank. Mast heights on 26-150 run 8–24 ft.
- Head tokens: `3` (1204), `1`, `2`, `4`, `(SL)3` (69) — searchlight-qualified — plus
  spelling variance (`(SL) 3`), unknowns (`X`, `SP`), and junk (`??`, `:`).
- Crossing tokens (~20 shapes): count-prefixed codes with bracket modifiers — `2F`,
  `1G`, `1G[PED]`, `1G[RD/PED]`, `M`, `M[SH]`, `C1L`/`C2L`/`C3L`, `P`, `1B`, `AHS`,
  `[VMS]`, `P[TL]`.

An open vocabulary with qualifiers means whole-configuration identities can never be
enumerated once; component decomposition prices the closed part (the components) and
maps the open part (the tokens) explicitly.

## Decision

Structures and crossings stop being special: injection decomposes each asset into
**component equipment lines** — the same `EquipmentInstance`-on-`SignalAsset` shape
turnouts and derails already use — and engineers price the component list once.

### 1. Component catalog, dimensions on the instance

The external catalog holds component items, not configurations:

- **Signal heads**: one item per aspect-count × head-kind the engineers price
  differently (`3-aspect colorlight`, `3-aspect searchlight`, …).
- **Structure bases**: `Mast <height> ft` as discrete items (heights are stepped, not
  continuous — which heights exist is the engineers' call from the 8–24 ft prod range);
  `Dwarf`; `Bridge (base)`; `Cantilever (base)` — crossing cantilever bases are
  per-lane-count items (`Cantilever 1-Lane`, `2-Lane`, `3-Lane`).
- **Crossing components**: `Flashing Pair`, `Gate`, `Ped Gate`, `Bell`, `VMS`, … as the
  token map (below) demands.

**Continuous dimensions live on the asset's line, never in the catalog identity.**
Bridge/cantilever pricing is *base + overage*: the base item covers its first
`included_ft` feet (e.g. "$50,000 up to 24 ft"), and a companion per-foot item carries
the overage as its **quantity** (`max(0, length − included_ft)`, unit `FT`). The length
is validated *before* the formula: an absent, zero, or negative length on a
length-priced type is a data gap — the asset **queues and its base is not priced**
(prod's `BRDG` rows include length 0, which is a missing-value sentinel, never a real
24-foot-covered bridge). A valid length at or under `included_ft` prices base-only with
zero overage — that is the intended case, not a gap. An over-limit length **requires the
per-foot companion**: if no overage component is mapped for the type, the asset queues
(base unpriced too — never silent base-only pricing for a length the base does not
cover); an overage line that exists but is unpriced reads as a readiness gap like any
unpriced line, never $0. Extended
cost stays `count × unit_cost` everywhere — no new pricing model, no workbook or grid
contract change (the `unit` column was carried for exactly this). `included_ft` rides
the base component as a small typed extension (the BatterySpec/ShellSpec pattern) —
pricing-adjacent data, owned where the engineers price. **One base per structure type**;
a second base is a design conversation, not a silent band.

The no-fallback rule covers the base pick too: a structure **type** with no mapped base
component (prod carries `MASTB`, `BRPST`, `OTHER`, and blank) queues, and a mast whose
height has no discrete catalog item queues — never defaulted, omitted, or rounded to
the nearest height. The structure-type → base-component resolution is part of the same
engineer-owned mapping surface as the token map.

### 2. Decode: typed grammar, engineer-owned token map

Two layers, shared by both families (and the reason this works for an open vocabulary):

- **Grammar is typed code** (ADR 0009): splitting `sig_config` into head tokens with
  their qualifiers attached and whitespace normalized (`(SL) 3` ≡ `(SL)3`); splitting
  crossing parts into count-prefixed tokens with bracket modifiers attached
  (`2F` → 2 × `F`; `1G[PED]` → 1 × `G[PED]`).
- **Token → component mapping is an engineer-managed table**, global like the catalog
  itself: `3` → `3-aspect colorlight`, `(SL)3` → `3-aspect searchlight`,
  `G[PED]` → `Ped Gate`, `M[SH]` → whatever the engineers name it. **No defaults, no
  fallbacks**: an unmapped token (including a qualified token whose base is mapped)
  lands loudly on the reconcile-external Injection queue with a one-click "map token" —
  a searchlight silently priced as a colorlight is exactly the error the queue exists to
  prevent. "Colorlight" itself is a mapping row, never an assumption.

The first injection run after the switch surfaces the project's full token vocabulary on
the queue; mapping it is minutes of engineer work that doubles as the sense-review
(greenfield posture — Signal Engineers are the oracle).

### 3. Labor

No new machinery: components are external-designated, so each already carries the
mat/lab pair. Per-component labor is the default; a per-structure installation figure is
just another component the engineers create and map. Their choice, expressed in data.

### 4. TIVS seams

- **Signal structures** (`sbis_prices.signal_equip` family flip for structures): stays
  per-record — a record's basis becomes the **sum of its SG asset's component lines**
  (base + overage + heads) instead of one resolved item's unit cost.
- **Crossings** keep the class-overlay shape (`sbis_prices.xing_equipment`): every asset
  with the same config string decodes to the same components, so SBIS **derives the
  class price** as Σ(component prices) and the TIVS overlay contract is unchanged.
  A class with any unmapped token or unpriced component derives no price — and a
  once-priced class in that state **re-installs as `UNPRICED`** (the existing Wave-4
  overlay sentinel), never as an absent row, so the xing calculator's missing-row $0
  default can never fire silently. Consumers must preserve the `UNPRICED` state.
- Seam version bumps; the flipped-path parity pins restate as component sums.

### 5. What retires

`StructureSpec`, banded matching, and the per-record resolved-item consumption patch;
the whole-string crossing classes. Cutover replaces the old lines in **one order**:
purge the whole-configuration items and their injected lines first, then re-inject
components (same pattern as #711: snapshot, one transaction, counts verified — and
re-injection is idempotent regardless, since component and whole-configuration lines
carry disjoint catalog items, the purge is what guarantees both line sets never coexist
on an asset to double-count). As of the decision
date (2026-08-04), prod held zero StructureSpecs and the SG/XN pricing flips had not
happened, so there was no priced state to migrate.

## Consequences

- Engineers price **one component list** (~15–25 items) instead of ~97+ identities plus
  every future configuration string; new configurations reuse existing prices and only
  genuinely new *tokens* ask for anything.
- Injection matching simplifies (no banding/ambiguity rules); the loud-queue posture is
  unchanged but the queue's unit becomes tokens, which converge, rather than
  configurations, which do not.
- Quantity-as-feet makes a length line's `Qty` read as feet in the grid and workbook —
  accepted; TIVS prices per-LF the same way. If it confuses in practice, a first-class
  dimension column is the graduation path.
- Data gaps surface honestly: a bridge with length 0/absent queues (its overage is
  incomputable), junk head tokens (`??`, `:`) queue, and `sig_struct_det` stops carrying
  identity weight (`SEARCHLIGHT` detail is redundant with the `(SL)` qualifier — the
  qualifier wins; disagreement is a queue-visible data question).

## Waves

1. **Decode core + token map** — pure grammar modules for both families (head tokens,
   crossing tokens) + the token-map table and its editor; unknown-token queue rows with
   one-click map/create. No injection change yet.
2. **Component injection** — SG/XN injection lands component lines through the decode
   (bridge base/overage from `included_ft`, mast height item pick); retire
   StructureSpec matching; reconcile-external queue speaks tokens.
3. **Seam rework** — per-record component sums for structures; derived class prices for
   the crossing overlay; seam version bump + parity pin restatement.
4. **Cutover** — engineers map tokens + price components on a real project; then, in
   the §5 order, purge the whole-configuration items and their lines and re-inject;
   flips proceed per family.

Open questions the waves must answer with the Signal Engineers: which mast heights are
priced steps; whether head kind splits beyond colorlight/searchlight; names for `M[SH]`,
`AHS`, `P`, `X`, `SP`; whether bridge overage is truly linear.
