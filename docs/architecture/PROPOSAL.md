# rmi-platform, rebuilt — architecture proposal

Task 0.7, 2026-09-30; revised by 0.8, 2026-10-02, for the operator's 2026-10-02 direction (MISSION.md)
and `docs/inventory/changes-since-2026-09-30.md`. Sources: `docs/inventory/` and `~/sources/`
(paths relative to each repo). Positions that needed a ruling are **[R-n]**, listed in §12; all were ruled on 2026-10-02.

## 1. Summary

- **The current direction is right; its contract is half-built**: about half of what a module *is*
  is wired by hand outside it (`seams.md` §3), links are URL strings, SBIS and TIVS import CIV.
- **A small core plus one declarative manifest per module**, read by API and worker; adding a
  module touches no file outside it (§3). Seams are typed, versioned, carry provenance, and carry
  prices *by reference* (§4).
- **Foundation chain:** `catalog` (what a thing is) → `pricing` (what it costs, per source, date
  and scope) → SBIS and TIVS (which value inventories). GIS domain codes are catalog identifiers;
  the catalog is the vocabulary authority (§7, §7A).
- **TIVS is a valuation framework with asset sub-modules** (source + filter, data dependencies
  only, exactly-one coverage, required properties and prices enforced at readiness) (§8.2).
- **GIS stays read-only**; the sync layer does the work; GIS schema changes go by proposal, ruled
  by the operator, applied by the GIS admin (§6). **All four carried-forward decisions stand** (§9).
- **Twelve small phases**; 26-150 data arrives before the SBIS and TIVS ports; the old platform
  takes only valuation-critical fixes, replayed via `docs/PARITY.md` (§10, §11).

## 2. Rebuild or evolve — [R-1]

A **new repository with a new core and contract, into which modules are *ported*, not rewritten**.

- **Write fresh:** core, manifest and registries, links and seams, sync contracts, kit, harness,
  catalog, pricing, the TIVS framework shell.
- **Port unchanged:** calculation functions (TIVS calculators, ADR 0009; CVS valuation; the PM fee
  engine) and CIV and SBIS workflows, as byte-identical moves with their tests (#1505, #1515).
  **Only the adapters feeding them change**: inputs come from asset sub-modules, child rows and
  pricing instead of `CalcField` lists, positional slots and `asset_cost`. Each sub-module's
  fixtures prove its numbers did not move; behaviour changes are separate tasks.

**Evolving in place** is viable and cheaper, but the catalog, pricing, GlobalID-only identity,
typed absence and child rows change schemas in every module; in a live system (v1.62.2, 114 open
issues) that is migration in flight. The cost is a data migration at cutover (§11, risk 2).
**Stack unchanged:** Python 3.12, FastAPI, htpy + HTMX, PostgreSQL (ADR 0002), ARQ, ruff +
pyright + pytest, uv workspace.

## 3. The core and the module contract

### 3.1 What the core owns (and nothing else)

| Core service | Change from today (`platform_core/...`) |
|---|---|
| identity (Portal OAuth, session, PAT) | non-Portal principal type reserved (#261), not built |
| access: project × module roles; **facets, capabilities, access keys declared by modules** | `PM_ACCESS_KEYS` and SBIS facets leave core (`access/service.py:94`, `access/models.py:53-66`) |
| projects, sections (+ section groups if #2026 is taken), parties | as is |
| module, link, seam registries; card slots; events | new: one loader, one `describe` |
| GIS sync engine and dataset contracts | §6 |
| audit; settings with **override-with-reason**; **revision counter** | one settings primitive; stamps use a monotonic counter, never `now()` (#2023) |
| **units** (§6.1) | new |
| jobs, cron, validation (ADR 0024), conversations (ADR 0019), documents, storage, kit and shell (ADR 0020) | registered via manifest; colour/label from the manifest, not `web/chrome.py:90-94` |

The core contains no domain words; CI greps `core/` for module keys (today it finds `sbis`, `pm`,
`pmfee`, `tivs`: `seams.md` §2.3).

### 3.2 The manifest

One typed pydantic model per module, found through an entry point (`rmi.modules`). `app.py` and
`worker.py` both call `load_modules()`, ending the "registered in one root, never fires" trap
(`sbis/composition.py:register_sbis_sync_hooks`).

```python
MANIFEST = ModuleManifest(
    key="sbis", version="1.0", display_name="Signal Bungalow Inventory", accent="teal",
    requires=[SeamRef("catalog.items", ">=1,<2"), SeamRef("pricing.prices", ">=1,<2")],
    uses=[SeamRef("pm.phase", ">=1,<2")],                      # absent -> feature off
    db_schema="sbis", core_revision=">=0005",
    routers=[web.router, api.router],
    permissions=Permissions(facets=["edit:inventory"], capabilities=[]),
    nav=[Nav("Bungalows", "/sbis/bungalows"), Nav("RR Audit", "/sbis/rr-audit")],
    gis=[Slot("bungalow", dataset="bungalows", required=True, writable_fields=())],
    jobs=[Job(tasks.generate_sheets)], on=[On("dataset.landed", "bungalows", hooks.adopt)],
    links_offered=[LinkKind("sbis.bungalow", identity=GisFeature("bungalows"), route=...)],
    relations=[...], cards_hosted=["civ.pano"],
    seams_offered=[SeamImpl("sbis.bungalow_estimate", "1.0", impl=seam.BungalowEstimate)],
    catalog_refs=[CatalogRef("sbis.instance", column="item_id")],   # "who points at me", §7.5
    validation=validation.provider, docs="README.md",
)
```

Anything the manifest does not declare, the module does not get.

### 3.3 Adding a module (the measure of modularity)

`docs/ADDING_A_MODULE.md`: (1) `scripts/new_module.py <key>` copies `modules/_template/` (package,
manifest, README, empty migration chain, one page, one test); (2) declare schema and models, `make
migrations`; (3) routes, nav, facets, kit components only; (4) needs: seams, GIS slots, link kinds,
cards, catalog refs; (5) offers: link kinds, cards, seams (`contracts/`, §4.3); (6) `pytest
modules/<key>`: `test_contract.py` builds the app with and without each `uses` provider and asserts
no page 500s, no link to an absent module, `describe` lists it; (7) record new decisions.

No file outside `modules/<key>/` and `contracts/<key>_*` changes; CI fails a module PR that edits
`core/`. `hello` (phase 1) and CVS (phase 4) prove the path. A TIVS asset type is a sub-module of
TIVS, not a platform module (§8.2).

## 4. Cross-module links, cards and seams

### 4.1 Identity is one type

Everything linkable has a **`Ref`** with a stable string form:
`gis:<dataset>:<GlobalID>` (GlobalID always, [R-3]); `oid:<dataset>:<OBJECTID>` (OID layers only,
ADR 0023, #1894); `<module>.<kind>:<id>` (e.g. `tivs.asset:turnout/{GlobalID}`);
`catalog.item:<id>` (merged items redirect); `pricing.price:<id>` (immutable). Asset ID is display only.

### 4.2 Links

- A module **offers** `LinkKind`s (name, identity kind, route, permission, label) and **declares
  relations** `(from_kind, to_kind, resolver)` ("GIS feature in `bungalows` → its SBIS bungalow").
- A page asks `links.for_ref(ctx, ref)` and gets links filtered by module presence, project
  enablement and grants, replacing `sbis/web/asset_cards.py:74-83`, `tivs/web/sbis_lines.py:172`,
  `civ/assets.py:43,76` and hand-written visibility checks (#435).
- **Stored links** (bungalow ↔ GIS feature, pairings) use a core `LinkStore` with create, relink,
  unlink and audit (#1950). Absent provider → no link, no error; `test_contract.py` checks it.

### 4.3 Seams (data that crosses)

A seam is a **contract package** (`contracts/sbis_bungalow_estimate/v1.py`): a `Protocol` plus
frozen pydantic DTOs, no implementation. The consumer asks `seams.get(BungalowEstimateV1)` and gets
the implementation or `None`.

- Major version in the name; an unsatisfied range fails start-up (`requires`) or turns the feature
  off with a reason (`uses`), replacing `EXPECTED_SEAM_VERSION` (`tivs/sbis_seam.py:31-35`).
- **Values carry provenance** [R-5]: `Provenanced[T] = (value, source, as_of, completeness,
  basis)` (#1434). **Money carries price refs, not copies**: the `pricing.price` refs and index
  values it rests on, which the consumer snapshots (§7A.5, §9.2).
- Identity and normalisation belong to the lowest owning layer (#1054). Dependencies are **per
  feature**: without SBIS, TIVS still values track and turnouts and reports bungalows "source absent".
- JSON Schema is generated from every contract and served by `describe`.

### 4.4 Cards

A card is a link that renders inline; the slot machinery (`web/slots.py:62`) stays. Its route, HTML,
JS and CSS live in the offering module, which declares the access rule (`grant="host"`, today's
behaviour in `civ/composition.py:34-38`). This cuts the 10 SBIS/TIVS imports of CIV web code.

### 4.5 Events

`dataset.landed` (today's sync hooks, #879), `phase.changed`, `link.changed`, `catalog.classified`,
`price.superseded`, `snapshot.sealed`; in-process via jobs, handlers from the manifest.

## 5. LLM-friendly conventions

- **`MAP.md`** (where things live, who owns which data, how to test), **`AGENTS.md`**, and a
  one-page `README.md` per module and per TIVS asset sub-module.
- **One layout per module** (`manifest.py`, `models.py`, `service/`, `web/`, `jobs.py`, `seams.py`,
  `migrations/`, `tests/`); **files ≤ 500 lines**, CI-enforced (#842).
- **Typed:** pyright strict on `core/` and `contracts/`; closed vocabularies are `StrEnum` with
  CHECK constraints (as `fee-estimate/SPEC.md` l.317).
- **Self-description:** `GET /api/v1/describe` / `rmi describe`: modules, routes, link kinds, seams
  with JSON Schemas, dataset contracts, TIVS sub-modules and filters, permissions, jobs, decisions.
- **One decision store** [R-2]: `docs/decisions/NNNN-*.md`, front matter `status: ruled | tabled |
  open | superseded`; ADRs 0001–0025 and `OWNER_RULINGS.md` imported as history; GIS schema
  proposals live here (§6.4).
- **Tests explain intent** and cite their issue; test DB from migrations (#928); async harness
  pinned on day one (#1943, #1951). **UI from the kit only** (#1592, #1927, #837).

## 6. Data and GIS layers

### 6.1 Database, data classes, absence and units

One schema and one Alembic chain per module plus `core` (ADR 0002). Three data classes: **synced**
(GIS copy), **owned**, and **evidence** (third-party material beside the inventory, compared via a
crosswalk and pairings; decisions recorded, never applied, reopened when their basis moves: ADR
0025, accepted 2026-09-30; the UP audit is the first case).

**Typed absence** [R-4]: core `Presence` = `present | undecided | excluded | absent | failed |
not_comparable(reason)`, for `include`, freshness, pricing gaps, unassigned records, evidence.
Every count surface shows excluded and failed counts (issues digest §3.2).

**Units** [R-11]: a small core vocabulary (`EA`; `TF, LF, MI`; `NT, GT`; `SY`; `CY, GAL`; `DAY,
HR`) and `Quantity(value, unit)`, converting only where defined (TF→NT needs a rail weight: a
calculation, not a conversion). Catalog properties, prices and TIVS quantities carry units; a
per-`TF` price times an `EA` count raises. #1213 (rail feet under an `NT` label, 3,326,825 vs
63,764) is this bug; `asset_cost.unit` is free text (`tivs/costing/models.py`).

### 6.2 GIS sync: one engine, one contract per dataset

ADR 0023 stays (one fetch per layer, refuse-empty with override #1689, freeze #1687, failed runs
shown failed #1837). Each dataset has one core-owned **dataset contract**, replacing ~410
`CalcField` uses:

| part | what | from `gis-schema-review.md` |
|---|---|---|
| `key` | GlobalID, or OBJECTID for OID layers only | §4, ADR 0023 |
| `envelope` | ~35 shared fields **from the live `FieldInfo`**; replaces `tivs/assets/envelope.py` | #2 |
| `slot_groups` | one **child row per non-empty slot**; related tables land in the same shape | #1 [R-6] |
| `links` | `rel_*` text → **GlobalID edges**; unresolved become findings | #4 |
| `derived` | `has_*`/`*_cnt` recomputed, never trusted for pricing; lat/long from geometry (#1042) | #3, #9 |
| `expectations` | ranges, regexes → advisory findings | #6 |
| `decode` | lenient domain matching, coercions, grammar decoders (`sig_config`, #908) | #5, #7, #8 |
| `capture` | domain + `OTH`/`TBD` + companion field, or the token family for legacy free text | §6.3 |

Storage: `core.gis_row` (raw `attrs` + `labels`, as `arcgis/synced.py:213`) with typed envelope
columns and lon/lat; `gis_child`, `gis_edge`, `gis_finding` alongside. A **drift check** compares
each sync's `FieldInfo` with the last (#729, #1042). Not PostGIS (ADR 0007). Shared datasets have
one owner (core, for `track_centerline`); `rmigis-pyt` YAML is never imported at runtime.

### 6.3 Inventory capture: domain first, free text only as the exception

Every inventory field that names a kind of thing is **a coded domain value** with two reserved
codes, **`OTH`** (not listed yet) and **`TBD`** (not determined), and **one companion text field**
used only with them, to name or describe it.

| captured | means | lands as |
|---|---|---|
| a listed code (`POWER`) | a known kind | the catalog class the code identifies (§7.3) |
| `TBD` (+ optional note) | not determined | `Presence.undecided`; readiness reports it by phase (ADR 0024) |
| `OTH` + text | something new | a catalog `unclassified` observation with the text verbatim (§7.4) |
| null | not captured | `Presence.absent`, never read as a default |

Free text is the deliberate, countable exception (curation shows `OTH`/`TBD` counts per field).
**For the GIS side, proposals only:** new and revised track-improvement layers and Survey123 forms
use this pattern (`gis-schema-review.md` #5: 21 trk domains lack an escape code; #6: 17 free
`_mfr`, 8 undomained `_type` fields). Today's escape is spelled `OTHER`
(`rmigis-pyt/templates/trk_impr_domains.yaml:620`); the contract maps it to `OTH`. Existing
free-text and slot fields are read through the catalog token map; unmapped text queues.

### 6.4 GIS schema changes: a proposal, a ruling, the admin applies [R-12]

Platform migrations are the per-module Alembic chains. **GIS schema** changes (layers, domains,
Survey123 forms) go this way, since the rebuild never edits `rmigis-pyt`:

1. **Proposal record** in the decision store (`kind: gis-schema-change`, status `open | ruled |
   applied | rejected`): change, reasons and issues, class P / T / O (`gis-schema-review.md`),
   impact on data, Survey123 forms, dataset contracts and consumers, rollback.
2. **Patch beside it**: the `rmigis-pyt/templates` YAML change as a diff in this repo.
3. **The operator rules; the GIS admin applies** it with `rmigis-pyt` (`sync_domains.py`,
   additive by default, `gis-tools-and-tiling.md`).
4. **Expand, then contract**: add first; consumers move with a dataset-contract version bump;
   retire the old field or code in a later proposal.
5. **The drift check confirms** the published layer, and the record becomes `applied`.

Catalog domain exports (§7.6) are one kind. An admin schema change is not a feature write, so
"GIS writes are attribute-only" (§9.1) is untouched.

### 6.5 GIS writes

See §9.1. The deferred change queue is a core service; modules declare `writable_fields`.

## 7. The shared equipment catalog

### 7.1 Where it lives: its own foundation module, `catalog` [R-7a]

Not core (domain data with its own curation, sources and queue). Pricing, SBIS and TIVS `require`
it. Seams `catalog.items` (lookup, resolve, classification, properties) and `catalog.observe`.

### 7.2 Shape (from `rmi-sbis-extract/docs/CATALOG_ENTRY_SPEC.md`, `PART_JSON_MODEL.md`)

- **Item**: one real thing or one **class**; `domain`, `classification` path, `status`
  (`classified | unclassified | merged(into)`), properties.
- **Properties are defined only by the catalog**: each domain's attribute schema gives name, type,
  **unit** (§6.1) and meaning (relay `coil_ohms`; turnout class `excluded_length`). A module that
  needs one gets it added to the domain; no private properties. **The catalog never makes a property
  mandatory** (a new thing can be `OTH`/`TBD` first); *required* belongs to a use (§8.2).
- **One standard, not per railroad**: one value per property, from RMI's chosen standard source, as
  a sourced claim (operator, 2026-10-02: "We don't differentiate between railroads"). Railroad
  part numbers stay identifiers (`rr_part_no`), not variants.
- **Identifier** (many per item): `value`, `issuer`, `kind` (`mfr_part_no`, `rr_part_no`,
  `stock_no`, `gis_code`, `legacy_sbis_id`, …), `source`, `valid_era`; all forms kept, compound
  strings raw beside split parts; unique per `(issuer, kind, value)`.
- **Relation** (`plugs_into`, `equivalent_to`, `part_of(qty)`); **claim** (per-property source and
  confidence, so corrections propagate; sources are `rmi-sbis-extract/conf/sources.tsv` ids such as
  `alstom-guide-2019 p.206`, later `reference.entry` refs); **token map** (generalises
  `sbis.component_token_map`; unmapped tokens queue, never default).
- **Prices are not catalog data** (operator agreed, 2026-10-02): they live in `pricing` (§7A).
  The extract catalog's reference prices are coverage, not valuation (owner, 2026-09-29); they
  seed pricing as a cited source.

Seed (`rmi-sbis-extract/catalog/`, 2026-09-30): 4,054 parts, 6,620 identifiers; SBIS's 505 rows
all answer to a part (276 / 49 / 180, `sbis_coverage.csv`); a battery row is a cell with a count.

### 7.3 Domains, and domain codes as catalog identifiers

| domain | seeds | consumers |
|---|---|---|
| `signal.relay`, `.timer`, `.rectifier`, `.battery`, `.charger`, `.transformer`, `.wiu`, `.comms`, `.track_interface`, `.logic_controller`, `.crossing_controller` | `rmi-sbis-extract/conf/dictionary/*`, the extract catalog, SBIS `equipment_catalog` (505 rows) | SBIS contents |
| `signal.head`, `.mast`, `.bridge`, `.cantilever` (ADR 0018) | SBIS external catalog + token maps | SBIS structures, TIVS signal structure |
| `crossing.gate`, `.flasher`, `.cantilever`, `.predictor` | SBIS crossing tokens | SBIS, TIVS crossing |
| `track.turnout`, `.complex_trackwork`, `.switch_stand`, `.switch_machine`, `.derail`, `.esl`, `.scc`, `.switch_heater`, `.frog`, `.point` | GIS domains `rmi_trk_to_complex_type`, `rmi_trk_stand_type` (HAND/POWER/DUAL), `rmi_trk_drl_type` (SLD/HNG/SWP/OTH), `esl_type` (`rmigis-pyt/templates/trk_impr_domains.yaml`) | TIVS turnout, complex trackwork, derail, rail/ties |
| `wayside.detector`, `site.*`; `service` (labor); `other` | GIS domains; SBIS labor rows | TIVS; pricing; anyone |

**Domain codes are catalog identifiers**: `issuer = "rmigis:<domain>"`, `kind = gis_code`. A code
usually names a *class* (`POWER` stand, `NML` turnout), so it maps to a classification node; an item
is attached when the model is known. The GIS domains and the catalog stay one vocabulary.

**`track.turnout`, the worked example.** A turnout class (frog size, rail section) carries
`excluded_length` (unit `TF`, standard source, as a claim), moved out of TIVS's transcribed table
(`tivs/assets/exclusions.py`, #239) as a relay's coil resistance lives in the catalog. Turnout never
reads it ("it is just a property of the turnout"); Rail and Ties read it through each turnout
record's class (#1414, #1373). The N/D connection-type gate (#239) is a Rail rule, in code.

**Bungalow function** (`rmi-sbis-extract/docs/BUNGALOW_FUNCTION.md`, each term proved by named
evidence) is a candidate domain once SBIS adopts it.

### 7.4 "Other / unclassified"

Anyone may record an unknown thing (`OTH` + text, §6.3; SBIS's form; a TIVS finding; an import).
It becomes an `unclassified` item in the nearest domain (or `other`) with the **raw text
verbatim**, who, when, where and source; references point at it like any item. Curation queues
these by frequency, beside "properties wanted" (§8.2) and "prices wanted" (§7A). Later, one of
two audited, reversible acts:

- **classify**: set domain, path and properties (and, if it is a new kind, it gets a code: §7.6);
- **merge**: point it at an existing item; it becomes `merged(into)`, keeps its raw text and
  identifiers as aliases, and every reference resolves through the redirect.

Nothing is deleted. The old `Other` and `*MULTIPLE UNKNOWN*` rows (`CATALOG_ENTRY_SPEC.md` §8)
migrate into this path.

### 7.5 Migration from `sbis.equipment_catalog`; who points at me

1. Load the extract project's parts and dictionaries as `classified` items with claims.
2. For each of the 505 old rows, run the extract project's loader mapping (old row → one or more
   items; row 115 "ACSP/DCSP" → 4 parts). Each old row becomes `legacy_sbis_id=<id>`; its
   `display_name`, `part_number`, `mfg_part_number`, `rr_ref_number` are kept raw and split.
3. Rows that do not resolve become `unclassified` items with their original text.
4. Instance rows re-point through a mapping table. **One row per item per bungalow, with a
   quantity**; confidence lives on the claims behind it. (0.7's `(bungalow, item, confidence)`
   let one relay count twice; withdrawn.)
5. `sbis.catalog_cost` rows become price records (§7A.7). A one-to-many split row is flagged for
   engineer review, never auto-divided.

**Who points at me.** Modules declare their catalog-referencing columns (`catalog_refs`, §3.2);
delete and merge consult that registry and a re-cut carries every reference across. Today
`catalog_delete.py` hard-codes its blockers, newest the RR Audit crosswalk
(`RrAuditFamilyItem.equipment_catalog_id`, RESTRICT; PARITY P-2/P-3; ADR 0025 l.126). Tested on
`fixtures/sbis/`, then on 26-150 data (phase 7); the real run is the operator's, at cutover.

### 7.6 Vocabulary authority: the catalog exports the GIS domains [R-12]

For equipment vocabularies **the catalog is the authority**, not the domain YAML. Classifying an
`OTH` into a new class creates a catalog item that needs a code in the GIS domain and the Survey123
choice list. The loop:

1. Classify → the catalog proposes a code (`issuer = rmigis:<domain>`, status `proposed`).
2. A job writes the **domain export** (`rmigis-pyt` domain YAML + Survey123 choice rows) as the
   patch of a GIS schema-change proposal (§6.4).
3. Operator rules; GIS admin syncs the domain; the drift check sees the code; it becomes `active`.
   Earlier `OTH` records stay as recorded, merged into the class.
4. A nightly check compares catalog-backed domains on the live layers with the catalog, both
   ways; a code added in the Portal first lands as `unclassified`.

## 7A. Pricing: its own module [R-7b]

### 7A.1 Where it sits

`catalog` → **`pricing`** → SBIS and TIVS. Pricing `requires` the catalog; SBIS and TIVS `require`
pricing. Seam `pricing.prices` resolves a price for an item or class, at a scope, escalated to a
date, with its references; link kind `pricing.price`. It answers "what does this cost, per this
source, at this scope, as of this date"; **it never values an inventory**.

### 7A.2 What it holds: the cost basis, and only that

| record | fields |
|---|---|
| **price** | `subject` (catalog item *or* class, e.g. POWER stand when the model is unknown); `material` and `labor` apart; `unit` (§6.1); `source`; `basis_date`; `scope` (`general` / `railroad:<party>` / `project:<id>`); `designator` (#1045); `active / superseded(by)`; who, when, note |
| **source** | `kind` (open: `published_catalog`, `estimators_guide`, `vendor_quote`, `engineer_estimate`, `railroad_price_list`, `prior_estimate`, …), citation, date, `visibility` (§7A.6) |
| **cost index** | series, publisher, values by period |
| **escalation** | `(price, index, from value, to value, factor, target date)` |

**Nothing is overwritten**: a correction supersedes, and every snapshot that cited the old record
still resolves.

### 7A.3 Scope and carry-over

Resolution: `project` → `railroad` → `general`, item before class. A project may **start from**
prices carried from earlier projects or general sources (operator: "often they are a good starting
point"): carrying creates a project record citing the carried one; overriding uses the core
override-with-reason primitive. Each line shows whether it was carried, entered or overridden.
Railroad scope is for *prices* (a railroad's price list); catalog *properties* stay one standard (§7.2).

### 7A.4 Escalation is normal, not an edge case

Often the only source is a 2019 catalog or a prior-year estimate (operator). The seam resolves a
price **to the run's valuation date** (§9.2) and returns the chain the reader sees:
"Alstom 2019 Estimator's Guide p.181, $X (2019-01), trended by <index> 2019-01 → 2026-06,
factor 1.27, project-scoped override by <who>: <reason>". A missing index value for the target
period is a typed gap, reported by readiness, never a factor of 1.

### 7A.5 Valuation logic stays in the modules; seams carry references

Extended cost, indirects, tax, depreciation and survivor curves, and rules such as "an unpriced
labor line poisons the labor leg" (OWNER_RULINGS 2026-09-25, #1957) stay in SBIS and TIVS. PM fee
billing rates stay in PM. SBIS still produces the pre-indirect bungalow estimate and only the
`(material, labor)` pair crosses to TIVS (#947, #1958), but **each value carries the price refs and
escalation it used**, so provenance travels by reference (#1434) and the snapshot freezes them.

**Double pricing becomes impossible by construction.** Today signal structures, crossing
equipment, detectors and switch machines can be priced in both SBIS (`catalog_cost`) and TIVS
(`asset_cost`), with `prices_from=SBIS` declarations and per-project `sbis_prices.*` flags choosing
(`tivs/assets/cost_tables.py:419,511`; #1440; #952 the shell priced twice). In the rebuild neither
module stores prices: one record per (subject, source, scope). Each component is counted by one
path per record (SBIS for bungalow contents, a TIVS sub-module for its components), and the
readiness gate fails a record whose cost cites the same price ref twice (the #952 case).

### 7A.6 Permissions are a reason for the module

Declared in the manifest as facets and capabilities: `pricing:view` (see prices and sources;
default SBIS/TIVS editors), `pricing:enter` (project-scoped prices and overrides), `pricing:curate`
(general and railroad scope, indexes, sources). **Source visibility** `public | firm |
restricted:<party>`: a railroad's confidential price list is usable only on that party's projects,
and elsewhere a price resting on a source the caller may not see shows "priced (restricted
source)" without the amount. **Restricted client principals** (#261) see no cost basis unless
granted. Today's `edit:costs` facet (`access/models.py:53`) moves from SBIS and TIVS to pricing.

### 7A.7 Seeds and migration

Seeds, `general` scope with basis years: the **2019 Alstom Estimator's Guide** (`rmi-sbis-extract`
`conf/sources.tsv`: `alstom-guide-2019`) and today's **TIVS cost books** (`tivs.asset_cost`, cost
table + named identity, `tivs/costing/models.py:41`). Cost-book rows become price records against
catalog classes (`hand_throw_stand` + stand type → `track.switch_stand/HAND`); `sbis.catalog_cost`
rows become project-scoped records on catalog items; `estimate_date` becomes `basis_date`. On
26-150 all 681 `asset_cost` and 428 `catalog_cost` rows were unpriced (#952), so early migrations
move mostly identities.

## 8. How the modules map onto it

| module | owns | offers | requires / uses | unbuilt work placed |
|---|---|---|---|---|
| **catalog** | items, classes, identifiers, properties, claims, token maps | `catalog.items`, `catalog.observe`, domain export | — / `reference.entry` | curation queue |
| **pricing** | prices, sources, indexes, escalations | `pricing.prices` | catalog | — |
| **CIV** | bookmarks, frame cache, markers | card `civ.pano`, feature → frames | OID dataset | frames API (#1982), embeddable card (#1232/#1233), `oid:` anchor (#1439) |
| **SBIS** | bungalows, instances (one per item, with quantity), RR Audit evidence | `sbis.bungalow`, seam `sbis.bungalow_estimate` v1 with price refs | catalog, pricing / `pm.phase`, `civ.pano` | GlobalID-first (#1061), unlink (#1950), #718/#723, labor (#1045, #1957), lump sums (#1990) |
| **TIVS** | runs with valuation date, snapshots, asset sub-modules | `tivs.asset`, `snapshot.sealed` | catalog, pricing / SBIS estimate, `pm.phase`, `civ.pano` | #410, #1414, #1099, #1213/#1373, #1434, #2029 |
| **PM** | properties, phase, fee estimates, billing rates | `pm.phase` v1; keys `pmfee`, `pmfin` | parties, QBO | fee rework after #1829; #1301 |
| **CVS** | valuation runs, reference data, published views | view API + `.pq` (PARITY P-7–P-9) | one dataset / `pm.phase` | port as is |
| **evidence**, **reference**, **reports** (later) | — | — | — | not in the build order |

The **RR Audit** (ADR 0025, PARITY P-1–P-6) is ported inside SBIS as it is; it moves to an
`evidence` module only when a second evidence source (GPX, client lists) appears.

### 8.1 Out of scope for now: land valuation, sales, and what "some love" for CVS could mean

**CVS is ported as is** ([R-9]); real-property layers and the corridor sales database (#1302) are
not designed (operator: "the module could use some love" later). From the issues, "some love" could
mean: platform-owned section groups (#2026), a monotonic view revision (#2023, in core anyway),
valuation year as a project fact (#950, tabled), the final legacy parity review (#598, #429). A
**sales/comparables** module could plug in later: it owns corridor sales with price and the ATF
basis divided against, with provenance (#1302), offers `sales.comparable` links and a seam CVS
`uses` for corridor-factor evidence, and reads CVS runs by `Ref` for valued-vs-sold.

**Not designed, by owner direction:** documents (#1298, #601, #1299, tabled 2026-09-18), valuation
year in PM (#950), strip maps (#131), BSIVS (#886).

### 8.2 TIVS: a valuation framework with asset sub-modules [R-13]

**The framework owns** runs (each with a valuation date), the stages (ADR 0009; Inventory → RCN →
Depreciation → RCNLD → Salvage → Obsolescence → Market value, `tivs/valuation/frames.py:198`),
readiness (ADR 0024), the snapshot, published frames and shared run/asset tables. **An asset
sub-module is one folder** `modules/tivs/assets/<key>/`, registered with TIVS, not the core (no
routes, nav or migrations per asset type):

```python
ASSET = AssetModule(
    key="turnout", label="Turnout",
    primary=Source("turnouts_cx", where=Eq("to_complex_type", "NML")),
    secondary=[],                                    # datasets it reads, never other sub-modules
    components=[Component("stand", catalog="track.switch_stand", slot_group="stand"), ...],
    requires_properties=[],                          # e.g. Rail: ("track.turnout", "excluded_length")
    requires_prices=["track.turnout", "track.switch_stand", "track.switch_heater"],
    rcn=rcn.turnout, depreciation=depr.turnout,      # ported calculators, unchanged (ADR 0009)
    detail_schema=TurnoutDetail, exhibit=exhibit.turnout, fixtures="fixtures/",
)
```

Shared tables hold typed common columns (quantity, unit, RCN legs, value) plus the declared detail
schema as validated JSON.

**Sub-modules depend on data, never on each other.** Rail depends on track and `turnouts_cx`, not
on the Turnout sub-module. Where facts live: a property of a *kind* → catalog; a cost → pricing; an
observation of *this* record → the GIS row; a valuation rule → sub-module code; firm-wide
parameters (rates, tax, scrap, obsolescence) → TIVS settings, frozen in the snapshot.

**Required properties and prices, enforced at readiness.** The catalog defines a property; a
sub-module *requires* it for its own use (Rail: `excluded_length` on every turnout class in its
secondary source; Turnout and SBIS do not); the framework enforces it at the readiness gate as a
locked rule (ADR 0024). A Rail run is blocked, naming the classes lacking it, instead of valuing
with a silent zero or default footprint (#1414; today `exclusions.py` falls back to the GIS length
or `None`, read as 0). The gaps also appear in curation as "properties wanted by tivs.rail";
unpriced required classes as "prices wanted".

**Every record lands in exactly one asset type.** Per source, the filters must be **disjoint and
exhaustive**: an unclaimed record is reported `unassigned` (typed absence); one claimed twice fails
the run. A filter may add "and not claimed by a narrower filter", so splitting is additive.

**Worked example: turnouts and complex trackwork.** Today both read `turnout_cx_inv_pt` through one
binding with row filters `to_complex_type == NML` and `!= NML` (`tivs/assets/turnout.py:320`,
`turnout_complex.py:194`; owner 2026-08-17). As sub-modules:

| sub-module | primary source | filter |
|---|---|---|
| `turnout` | `turnouts_cx` | `to_complex_type = 'NML'` |
| `complex_trackwork` | `turnouts_cx` | `to_complex_type <> 'NML'` and not claimed |
| later `dslip`, `lap_sw`, `to_mpf`, `dia_mpf` (#410; 26-150: 27 / 3 / 17 / 8 records) | `turnouts_cx` | `= 'DSLIP'` … |

Adding `dslip` narrows `complex_trackwork` without editing it; the coverage check proves nothing
moved twice or vanished. **[R-13a], ruled 2026-10-02:** an empty `to_complex_type` is `undecided`. Today `!= NML` keeps NULLs
(`tivs/assets/types.py:84`), valuing them as complex trackwork; instead it is unclaimed, reported
`unassigned`, and blocks valuation.

**Era-mixed sources** (`turnout_inv_pt` / `turnout_cx_inv_pt`; the wayside pair): alternative
sources, one chosen by the project's GIS binding as today (`turnout.py` docstring); binding both
fails readiness.

**Valuation date.** Every TIVS run carries an as-of date, frozen in the snapshot; pricing escalates
to it. This does not reopen #950 (tabled): the run carries its own date.

**Checklist** (`ADDING_AN_ASSET.md`): copy `_template`; source + filter; coverage check; components,
required properties and prices; calculators; fixtures with the old platform's numbers; README.

### 8.3 Later modules: the reference hub and report production

**Reference hub** (not designed): offers `reference.entry`; catalog claims and pricing sources hold
a `Ref` *or* citation text, linked once it exists; pages show references via `links.for_ref`, nothing
while absent. First content: `rmi-sbis-extract/docs/EQUIPMENT_DOCUMENT_LIBRARY.md`. Reference
material, not project records, so #1298's tabling does not apply. **Report production** stays out
(operator: "perhaps a future module"); nothing is designed; it would read sealed snapshots (§9.2).

## 9. The carried-forward decisions

### 9.1 GIS writes: attribute updates only, deferred queue with old-value guard — **stands**

Nothing argues against it (ADR 0016 §4 agrees). The issues add (#1220-1225): pending-change
overlay on reads, `writable_fields`, capability `gis.write_back` (`access/models.py:68`, unused),
dry-run, conflict-rate halt, per-field approval, rollback by inverse change. Row: `(dataset,
GlobalID, field, old, new, who, when, reason, status)`. Built last; first use the `rel_*` backfill
(#1002). Schema changes are a separate, admin-applied path (§6.4).

### 9.2 TIVS snapshots what persists with a valuation — **stands, extended**

`TivsValSnapshot` stamps `data_basis` per source run and `git_sha` (`tivs/valuation/models.py:42-70`),
but #2029 shows rates, tax, scrap, obsolescence and depreciation assignments are not frozen and
frames are re-aggregated at read time. The rebuilt snapshot freezes: (1) the **valuation date** and
run settings; (2) per record, **which sub-module and filter valued it** and its inputs (child rows,
edges, catalog classes and property values, raw identifiers); (3) **every price ref, source and
index value** used, including those behind the SBIS estimate (#1434); (4) the coverage result and
the computed frames. Report time reads only the snapshot; staleness is a comparison of stamps.

### 9.3 CIV is built on the OID as catalog; only the viewer is third-party — **stands**

OID layers are the one OBJECTID-keyed class (ADR 0023 amendment); the frames API (#1982) has the
browser read synced `oid` rows, not the feature service. Photo Sphere Viewer and the ArcGIS Maps
SDK stay the only third-party parts; tiles follow `tile-contract.v1.json`. The **standalone viewer
(#1981) is now its own project** (client-hosted on Azure, owner 2026-10-01); the rebuild owes it the
OID/frames shape only. #437 (CIV-only mode for clients on RMI) waits with #261.

### 9.4 Fee estimator rules are configurable, with overrides and justification; effort in days — **stands**

`SPEC.md` §5 shows days, stores hours (l.46, 76); seeds are editable defaults; override category
and note live on the line (l.333). #1829 is about fit, not this rule. Port unchanged, use the core
override primitive, wait for the owner's scope; calibration cases report deltas, not asserted.

## 10. Build order

Each phase ends with green CI and a journal entry; `coder`-sized unless marked. Cutover is the
operator's decision.

1. **Harness and contract**: skeleton, pinned async harness, CI (ruff, pyright, pytest, 500-line
   cap, migrations from scratch, "module PR touches no core"), `MAP.md`, manifest and loader,
   `describe`, `_template` + `hello` + `test_contract.py`, decision store. *(heavy for the contract)*
2. **Core services**: identity, access, projects, audit, settings with override-with-reason,
   revision counter, **units**, kit shell, link/seam registries, cards, events, jobs.
3. **GIS sync engine**: landing, refuse-empty, freeze; dataset contracts incl. `capture`, drift
   check, `Presence`; the schema-change proposal record (§6.4). Fixtures and synthetic layers.
4. **CVS port** ([R-9]), with its published views and `.pq` files (PARITY P-7–P-9).
5. **CIV port**: OID frames API, markers via relations, `civ.pano` card with host grant.
6. **Catalog**: model, attribute schemas, unclassified path, token maps, curation, extract loader,
   `catalog_refs`, domain export (§7.6), `equipment_catalog` migration on fixtures.
7. **Real data arrives** *(operator step, a gate)*: the operator places project **26-150** in
   `data/` (restore extract of SBIS and TIVS tables and synced GIS rows); the catalog migration is
   re-run on it. Nothing derived that identifies a client is committed.
8. **Pricing**: records, sources, indexes, escalation, scope and carry-over, permissions; seeds
   (2019 Alstom guide, TIVS cost books); `catalog_cost`/`asset_cost` migration checked on 26-150.
9. **SBIS port** on catalog and pricing: GlobalID-first, one instance per item, unlink,
   `sbis.bungalow_estimate` v1 with price refs, validation, RR Audit, CIV card.
10. **TIVS port**: the framework first (runs with valuation date, stages, readiness, coverage,
    snapshot §9.2); then sub-modules one at a time, **turnout and complex trackwork first**, then
    rail/ties (excluded length from the catalog), each proving its 26-150 numbers unchanged.
11. **PM port** (fee engine unchanged, calibration fixtures).
12. **Write-back** (§9.1); the **evidence** module when a second evidence source exists.

Before each module's cutover, every PARITY row touching it is replayed or ruled not needed. After
these: cutover planning (operator runs scripts on a restore copy), client access (#261, #437),
archive capsule (#455, #1423), the reference hub. **Ops are constraints now, built at cutover**
[R-10]: config apart from secrets (#1394), tag deploy with approval (#1401), private DB (#1403),
restore drill (#1400, #1424).

## 11. Risks

1. **The rebuild never catches up while the old platform keeps delivering** ("we have active
   projects"). Mitigation [R-14]: **rmi-platform takes only changes needed to complete a
   valuation**, each labelled **`rebuild:replay`** on its issue (the snapshot carries labels) with
   a "**Rebuild impact:** none / replay / supersedes" PR line. Snapshot refreshes add labelled
   issues to **`docs/PARITY.md`**, where each row is replayed or ruled not needed, checked before
   each module's cutover (21 commits landed in two days, 2026-09-30, shows why).
2. **Data migration at cutover** (GlobalID-first SBIS, catalog re-key, price records, child rows).
   Phase 7 tests the scripts on 26-150; the operator runs them first on a restore copy. Largest
   unknowns: SBIS rows with no GlobalID, catalog rows that split, cost-book identities with no class.
3. **Pricing grain and migration.** Class vs item grain (stand class vs model; GCP 4000 assembly vs
   modules; crossing labor, #809) is the owner's; the model holds both, item before class.
   Cost-book identities with no catalog class migrate as `unclassified` subjects, never dropped.
4. **Filter coverage on era-mixed data**: Schema-1/2 pairs and `OTHER`/NULL codes can leave records
   unassigned or double-claimed; the coverage check makes it loud, likely on first 26-150 runs.
5. **Vocabulary drift** while the export loop waits on a human: nightly drift check, both ways.
6. **Small-model builders**: 500-line cap, one layout, contract tests, heavy review at phase ends.
7. **The CIV card cut** must reproduce today's access; a test pins `grant="host"`.
8. **Budget**: heavy tier only for the contract and reviews.
9. **Owner questions gate parts of phases 8–11**: rail basis (#1373), crossing labor (#809),
   tie-share fields (#2029, integers read as fractions), NULL `to_complex_type` ([R-13a]), CIV
   anchor (#1439). Dependent tasks are marked blocked.
10. **Not verified:** live layers vs templates, Survey123 field use, runtime seams, the full
    `sbis.seam` DTO list, how cleanly cost-book identities map to catalog classes.

## 12. Operator rulings

All ruled 2026-10-02 in `approvals/architecture.md` ("Approved: docs/architecture/PROPOSAL.md as
revised by task 0.8"). "Accepted" means as recommended; additions are the operator's.

| # | recommendation (details in the section cited) | ruling |
|---|---|---|
| R-1 | New repo; modules ported: calculators unchanged, adapters change, fixtures prove numbers (§2). Evolve-in-place is the viable, cheaper alternative. | **Ruled: accepted.** |
| R-2 | One decision store; ADRs 0001–0025 and `OWNER_RULINGS.md` imported as history (§5). | **Ruled: accepted.** |
| R-3 | GlobalID the only GIS key; OBJECTID only for OID datasets (§4.1). | **Ruled: accepted.** |
| R-4 | Typed absence (`Presence`), incl. `TBD` and `unassigned` (§6.1). | **Ruled: accepted.** |
| R-5 | Seam values carry provenance; money carries price refs (§4.3). | **Ruled: accepted.** |
| R-6 | Slot groups become child rows on sync (§6.2). | **Ruled: accepted.** Measured on the 26-150 forms: 557 of 1,866 questions are numbered slots (Complex Turnout 268 of 512, 101 groups); one repeat group in all 12 forms. |
| R-7a | Catalog: own module; sole definer of properties, none mandatory; one standard value per property, no per-railroad variants; vocabulary authority exporting GIS domains (§7). | **Ruled: accepted.** |
| R-7b | Pricing: own module; cost basis only; scope and carry-over; escalation chain; no overwrite; permissions and source visibility; seeds (§7A). | **Ruled: accepted;** keep pricing scope `general` / `railroad` / `project`. |
| R-8 | Overtaken: standalone CIV viewer is its own project (#1981); CIV anchor on `oid:` refs (§9.3). | **Ruled: noted (overtaken).** |
| R-9 | CVS ported as is, first contract test; land and sales out of scope (§8.1). | **Ruled: accepted.** |
| R-10 | Ops are constraints now, work at cutover (§10). | **Ruled: accepted.** |
| R-11 | Core units vocabulary and `Quantity` (§6.1). | **Ruled: accepted.** |
| R-12 | Capture = domain + `OTH`/`TBD` + companion text; GIS schema changes by proposal → ruling → GIS admin (§6.3, §6.4, §7.6). | **Ruled: accepted, with:** existing `OTHER` maps to `OTH`, and `UNK`/`UNKNOWN` to `TBD`; each field gets its **own** companion text, shown only when `OTH`/`TBD` is chosen (not one `notes_other` per form); Survey123's `or_other` is not used. Today 69 of 128 choice lists have an escape code, spelled four ways. |
| R-13 | TIVS framework + asset sub-modules; valuation date per run (§8.2). | **Ruled: accepted.** |
| R-13a | Empty `to_complex_type` = normal turnout or undecided? (proposed: undecided). | **Ruled: undecided** (unassigned, blocks valuation). |
| R-14 | Old platform takes only valuation-critical changes, `rebuild:replay` label + PR line, `docs/PARITY.md` (§11). | **Ruled: accepted;** rmi-platform starts using the `rebuild:replay` label now. |
| — | Cost index selection (§7A.4). | **Decided in the pricing phase:** a default index per catalog domain, overridable per project with a reason. |
| — | Tabled items stay tabled; reference hub and reports are later modules; fee rework waits for #1829. | Unchanged. |

**Note from the operator:** `docs/inventory/survey123.md` is unreliable in places (guessed layer
names, hedged claims; it calls wayside detectors non-valued, which contradicts this proposal). Use
the measured figures above; the form inventory is redone with a parser in the catalog phase (§10, 6).
