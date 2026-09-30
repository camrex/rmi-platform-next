# rmi-platform, rebuilt — architecture proposal

Task 0.7, 2026-09-30. For the operator to approve, change or reject at the checkpoint.
Sources: the inventories in `docs/inventory/` (cited by file name) and the read-only clones in
`~/sources/` (paths relative to each repo). Wherever this document takes a position on a question
the operator has not ruled on, it is marked **[R-n] recommendation**; §12 lists them for ruling.

## 1. Summary

- **The current platform's direction is right; its contract is half-built.** `platform_core`
  imports no module code, modules have their own schemas and Alembic chains, and four version-checked
  seam adapters exist (`seams.md` §1). But about half of what a module *is* (routers, hooks, tasks,
  cron, settings, access keys, card slots, resolvers, launcher entry) is wired by hand in about nine
  files outside the module (`seams.md` §3). Links between modules are hard-coded URL strings, and
  SBIS and TIVS import CIV's web code directly.
- **The rebuild is a small core plus one declarative module contract.** A module is one package
  with one manifest. The core reads that manifest, in both the API and the worker, and wires
  everything from it. Adding a module touches no file outside it (§3).
- **Seams and links are first-class, typed and versioned.** Modules never import each other. They
  depend on small *contract* packages, and the core's registry answers "is there a provider, is it on
  for this project, may this user see it". If the provider is absent, the link or card simply does
  not appear (§4).
- **The equipment catalog becomes its own foundation module**, seeded from `rmi-sbis-extract`. Both
  SBIS and TIVS consume it. One canonical entry per real item keeps every identifier form, and an
  explicit *unclassified* path records new things now and classifies them later without losing
  anything (§7).
- **GIS stays read-only in the Portal. The sync layer does the work:** it builds the envelope from
  the live `FieldInfo`, turns slot groups into child rows, turns `rel_*` text into GlobalID edges,
  and records expectations, findings and typed absence. None of this needs a Portal change (§6,
  from `gis-schema-review.md`).
- **All four carried-forward decisions stand** (§9). None was shown wrong. Two gain detail from the
  issues: write-back gets overlay, dry-run, halt, approval and rollback; the fee estimator's *rules*
  decision stands but its *implementation* is under owner review (#1829).
- **Build order: ten small phases**, starting with the harness and contract and ending with
  write-back. The reference hub comes after all of them (§10).

## 2. Rebuild or evolve — [R-1]

The operator asked for a rebuild from scratch. The evidence supports a **new repository with a new
core and contract, into which modules are *ported*, not rewritten**:

- Write fresh: the core, the manifest and registry, the links and seams, the sync layer's contract,
  the kit, the test harness, the catalog. These are exactly the places where the findings demand a
  different shape.
- Port, keeping behaviour: TIVS calculation code (code-owned by ADR 0009, 48 migrations of learned
  rules), CVS valuation (parity-proven), CIV viewer, SBIS workflows, PM fee engine. Ports should be
  byte-identical moves with their tests, the same rule the current project uses for extractions
  (#1505, #1515). Behaviour changes become separate tasks.

The honest alternative is to **evolve rmi-platform in place**: finish the manifest, add the link and
seam registries, and cut the CIV leak. That would be cheaper and it is viable. The rebuild is still
worth it because the catalog, GlobalID-only identity, typed absence and slot child rows change
schemas in every module, and doing that inside a live system (v1.59.1, ~116 open issues) means
migrating in flight. A clean repo lets each change land once, behind tests, without production data.
The cost is a data migration at cutover (§11, risk 2).

**Stack: unchanged.** Python 3.12, FastAPI, htpy + HTMX, PostgreSQL (schema per module, ADR 0002),
ARQ on Redis behind the `enqueue` boundary, ruff + pyright + pytest, uv workspace. Nothing in the
issues argues for a different stack, and changing it would only add risk.

## 3. The core and the module contract

### 3.1 What the core owns (and nothing else)

| Core service | Carried from | Change |
|---|---|---|
| identity (Portal OAuth, session, PAT) | `platform_core/identity`, `tokens` | principal type for non-Portal users reserved (#261), not built |
| access: project × module roles, **facets, capabilities and access-only keys declared by modules** | `platform_core/access` | remove `PM_ACCESS_KEYS` and SBIS facets from core (`access/service.py:94`, `access/models.py:53-66`) |
| projects, sections, parties | `projects`, `sections`, `parties` | as is |
| module registry, link registry, seam registry, card slots, events | `registry/manifest.py`, `web/slots.py` | new: one loader, one describe API |
| GIS sync engine and dataset contracts | `arcgis/` | §6 |
| audit (transactional), settings with **override-with-reason** | `audit/db.py`, `*_setting` tables | one settings primitive replaces per-module setting tables |
| jobs (ARQ), cron, metrics | `worker/` | jobs come from manifests |
| validation engine, conversations | ADR 0024, ADR 0019 | registration via manifest |
| documents (PDF), storage | `documents/`, `storage/` | as is |
| web kit and shell | ADR 0020 `web/` | module colour/label from the manifest, not `web/chrome.py:90-94` |

The core contains no domain words: no bungalow, no turnout, no fee. The test is that `grep` finds
no module key in `core/` (today it finds `sbis`, `pm`, `pmfee`, `tivs`: `seams.md` §2.3).

### 3.2 The manifest

One typed pydantic model per module, validated at load. Modules are found through a Python entry
point (`[project.entry-points."rmi.modules"]`), so the workspace member is the only registration.
Both `app.py` and `worker.py` call the same `load_modules()` and nothing else. That removes the
"registered in one root, silently never fires" trap (`sbis/composition.py:register_sbis_sync_hooks`
docstring).

```python
MANIFEST = ModuleManifest(
    key="sbis", version="1.0", display_name="Signal Bungalow Inventory", accent="teal",
    requires=[SeamRef("catalog.items", ">=1,<2")],             # start fails with a named reason
    uses=[SeamRef("pm.phase", ">=1,<2")],                      # absent -> feature off
    schema="sbis", migrations="sbis/migrations", core_revision=">=0005",
    routers=[web.router, api.router],                          # core applies literal-before-param order
    permissions=Permissions(facets=["edit:inventory", "edit:costs"], capabilities=[]),
    nav=[Nav("Bungalows", "/sbis/bungalows")], config=[...], settings=[...],
    gis=[Slot("bungalow", dataset="bungalows", required=True, writable_fields=())],
    jobs=[Job(tasks.generate_sheets)], cron=[], on=[On("dataset.landed", "bungalows", hooks.adopt)],
    links_offered=[LinkKind("sbis.bungalow", identity=GisFeature("bungalows"), route=...)],
    relations=[Relation("sbis.bungalow", "gis.feature", resolver=...)],
    cards_offered=[], cards_hosted=["civ.pano"],
    seams_offered=[SeamImpl("sbis.priced_inventory", "1.0", impl=seam.PricedInventory)],
    anchors=[...], validation=validation.provider, capsule=None, docs="README.md",
)
```

Every field maps to something `seams.md` §6 found wired by hand. Anything the manifest does not
declare, the module does not get: no side registration.

### 3.3 Adding a module (the measure of modularity)

`modules/_template/` is a working module that does nothing, and `scripts/new_module.py <key>`
copies it. A new session follows `docs/ADDING_A_MODULE.md`, which is this checklist:

1. `new_module.py <key>`: package, manifest, `README.md`, empty migration chain, one page, one test.
2. Declare the schema and write models; `make migrations` generates the first revision into the
   module's chain.
3. Declare routes, nav, facets. Use kit components only (no inline CSS or JS).
4. Declare what you need: `requires` and `uses` seams, GIS slots, link kinds you show, cards you host.
5. Declare what you offer: link kinds, cards, seams (a contract package under `contracts/`, §4.3).
6. Run `pytest modules/<key>`. The template ships `test_contract.py`, which loads the manifest,
   builds the app with and without each `uses` provider, and asserts that no page 500s, no link
   points at an absent module, and `describe` lists the module.
7. Add the module to the ADR index if it introduces a decision.

No file outside `modules/<key>/` and `contracts/<key>_*` changes. CI enforces this with a check
that fails if a PR adding a module edits `core/`. Two modules written early prove the path: the
template's `hello` module (phase 1) and CVS, the cleanest real module (phase 4).

## 4. Cross-module links, cards and seams

### 4.1 Identity is one type

Everything that can be linked has a **`Ref`** with a stable string form. Four kinds cover
everything found in `seams.md` §6.2:

| kind | string form | key |
|---|---|---|
| GIS feature | `gis:<dataset>:<GlobalID>` | GlobalID, always ([R-3]) |
| OID frame | `oid:<dataset>:<OBJECTID>` | OBJECTID, declared on the dataset (ADR 0023 amendment, #1894) |
| module record | `<module>.<kind>:<id>` | module-owned id (e.g. `tivs.asset:turnout/{GlobalID}`) |
| catalog item | `catalog.item:<id>` | catalog id; merged items redirect (§7) |

Asset ID is a display attribute and never a key. OBJECTID is a locator, except for OID frames.

### 4.2 Links

- A module **offers** a `LinkKind`: name, identity kind, route template, the permission needed to
  open it, and a label.
- A module **declares relations** `(from_kind, to_kind, resolver)`: "a GIS feature in `bungalows`
  → its SBIS bungalow", "a GIS feature → nearest OID frames". Resolvers are async functions over the
  owner's data.
- A page asks `links.for_ref(ctx, ref)` and gets back the visible links, already filtered by
  module presence, project enablement and caller grants. The kit renders them. This replaces
  `sbis/web/asset_cards.py:74-83`, `tivs/web/sbis_lines.py:172`, `civ/assets.py:43,76` and the
  per-link visibility checks (`sbis/web/routes.py:1355-1369`, `pano_card.viewer_link`). #435 asked
  for exactly this.
- **Stored links** (bungalow ↔ GIS feature, evidence pairings) belong to the module that owns them
  and use a core `LinkStore` with create, relink and unlink, audit, and a `link.changed` event.
  That gives #1950 (unlink) a place to live.
- Absent provider → no link, no gap, no error, by construction. `test_contract.py` checks it.

### 4.3 Seams (data that crosses)

A seam is a **contract package** (`contracts/sbis_priced_inventory/v1.py`): a `Protocol` plus
frozen pydantic DTOs, and no implementation. The offering module implements it; the consumer
imports only the contract and asks `seams.get(PricedInventoryV1)`, which returns the implementation
or `None`. Rules:

- Major version in the name; minor changes are additive. The registry refuses a consumer whose
  range is not satisfied: it fails start-up for `requires` and turns the feature off with a named
  reason for `uses`. This replaces the hand-bumped `EXPECTED_SEAM_VERSION` (`tivs/sbis_seam.py:31-35`).
- **Values that cross carry provenance.** `Provenanced[T] = (value, source: Ref, as_of,
  completeness, basis)`. This fixes #1434, where SBIS's `estimate_date` and completeness are lost at
  the crossing. [R-5]
- Identity and normalisation belong to the offering side, the lowest layer that owns the data
  (#1054). Consumers do not re-collapse.
- Dependencies are **per feature, not per module**: TIVS `requires` the catalog, but only `uses`
  SBIS. Without SBIS, TIVS values track, turnouts and crossings and reports bungalows as
  "source absent". Today TIVS cannot start without SBIS (`seams.md` §4).
- JSON Schema is generated from every contract and served by `describe` (§5).

### 4.4 Cards

A card is a link that renders inline. The existing slot machinery (`web/slots.py:62`: renderer
`(SlotContext) → node | None`, SAVEPOINT, errors healed to "no card") stays. Changes:

- A card accepts a declared identity kind.
- The card's route, HTML, JS and CSS live entirely in the offering module and are served from its
  static path.
- The offering module declares its access rule, e.g. `grant="host"`: "anyone who may see the host
  page may see this card". That keeps the current deliberate behaviour (`civ/composition.py:34-38`)
  without the host importing CIV. This cuts the one real leak: 10 import lines from SBIS/TIVS into
  CIV web code.

### 4.5 Events

The events are `dataset.landed(project, dataset, run)` (today's sync hooks, each isolated and
recorded on the run, #879), `phase.changed`, `link.changed` and `snapshot.sealed`. They are
in-process and dispatched through jobs, not a message bus. Handlers come from the manifest.

## 5. LLM-friendly conventions

A new session of any model should find its way in minutes.

- **`MAP.md`** at the root: one screen that says where each kind of thing lives, which module owns
  which data, and how to run tests. **`AGENTS.md`**: the rules. Each module has a `README.md` of at
  most a page: purpose, owned data, seams offered and consumed, open decisions.
- **One layout per module:** `manifest.py`, `models.py`, `service/` (logic, no web), `web/`
  (routes, pages), `jobs.py`, `seams.py` (implementations of offered contracts), `migrations/`,
  `tests/`. The template enforces it.
- **Small files.** CI enforces a hard cap of 500 lines, because the builders include 16k-context
  local models, and #842 shows what happens without one (a 3,082-line routes file).
- **Typed throughout:** pyright strict on `core/` and `contracts/`, and closed vocabularies are
  `StrEnum` with generated CHECK constraints. The fee spec already does this
  (`docs/planning/pm/fee-estimate/SPEC.md` l.317).
- **Machine-readable self-description.** `GET /api/v1/describe` (PAT-scoped) and `rmi describe`
  (CLI) return modules, versions, routes, link kinds, relations, seams with JSON Schemas, datasets
  with their contracts, permissions, jobs, and decisions with status. `tools/rmi-mcp` becomes a
  client of it.
- **One decision store** [R-2]: `docs/decisions/NNNN-*.md` with front matter
  `status: ruled | tabled | open | superseded`, `issues: [...]`, `modules: [...]`. The ~47 dated
  sections of `OWNER_RULINGS.md` and ADRs 0001–0025 are imported once as history, indexed and
  linked from manifests. `describe` serves the index.
- **Tests explain intent:** names state the rule (`test_unpriced_labor_line_poisons_labor_leg`), and
  every issue-derived rule cites its issue in the docstring. The test DB is built from migrations
  (#928). The async harness is pinned on day one: explicit loop scopes, a single async plugin, and
  documented connection strategies. The CI loop flake (#1943, #1951) cost months.
- **UI built from the kit only.** No CSS, JS or URL assembled in Python strings (#1592, #1927,
  #837). URLs come from a helper that quotes identifiers. Refused requests appear in one kit place
  (#1690, option A).

## 6. Data and GIS layers

### 6.1 Database

One PostgreSQL database with one schema per module plus `core` (ADR 0002). Each module has its own
Alembic chain with its own version table, declares the core revision it needs, and never depends on
another module's migrations. `project_id` stays an unconstrained UUID in module tables. Three
data classes, by origin: **synced** (GIS copy, read-only), **owned** (a module's records),
**evidence** (third-party material that sits beside the inventory and is never merged into it,
ADR 0025).

**Typed absence** [R-4]: a core `Presence` vocabulary, `present | undecided | excluded | absent |
failed | not_comparable(reason)`, used for `include`, sync freshness, pricing gaps and evidence
comparison. Every count surface shows its excluded and failed counts. This is the root cause of
issues-digest §3.2 (#1040, #822, #1558, #1837, #1572 and more).

### 6.2 GIS sync: one engine, one contract per dataset

The ADR 0023 posture is kept: one Portal fetch per layer, module derivations from the platform
copy, the refuse-empty guard with a one-shot override (#1689), one platform-wide freeze (#1687), and
a failed latest run shown as failed (#1837). What changes is that each dataset has one declared
**dataset contract**, owned by the core and shared by the modules that bind it, rather than each
module's hand-typed `CalcField` list (~410 uses):

| part | what | from `gis-schema-review.md` |
|---|---|---|
| `key` | GlobalID, or OBJECTID for OID layers only | §4, ADR 0023 |
| `envelope` | the ~35 shared fields, **generated from the live `FieldInfo`** with loud type-mismatch gaps; replaces `tivs/assets/envelope.py` | #2 |
| `slot_groups` | prefix, suffixes, max index → one **child row per non-empty slot** `(feature, group, position, attrs)`; related tables such as `xing_struct_tbl` and `wayside_det_eq_tbl` land in the same shape | #1 [R-6] |
| `links` | `rel_*` asset-ID text resolved to **GlobalID edges** `(from, to, via_field)`; unresolved or ambiguous become findings | #4 |
| `derived` | `has_*` and `*_cnt` recomputed and compared, never trusted for pricing; lat/long from geometry when null, labelled `derived` (#1042) | #3, #9 |
| `expectations` | ranges and regexes per field → advisory `out_of_range` findings | #6 |
| `decode` | case- and type-insensitive domain matching; coercion table (dates, angles, lengths); grammar decoders (`sig_config`, `equip_summary`, tank sizes #908) | #5, #7, #8 |

Storage: `core.gis_row` (raw `attrs` + `labels` as today, `GisDatasetRow` in
`arcgis/synced.py:213`), plus typed generated columns for the envelope, a sortable
`(subdivision, milepost)`, and point geometry as lon/lat (lines as GeoJSON). A `gis_child`,
`gis_edge` and `gis_finding` table sit alongside. A **drift check** compares each sync's `FieldInfo`
with the previous one; it would have caught #729, #1042 and the APN truncation. **Not PostGIS** for
now (ADR 0007). Revisit if spatial queries outgrow lon/lat and `rows_near`.

A shared dataset has a declared **owner** (the core, for `track_centerline`); every module binding
it is a reader (`seams.md` §2.4). The `rmigis-pyt` YAML stays the owner's build documentation. The
platform never imports it at runtime (review, "what this means" #2).

### 6.3 GIS writes

See §9.1. The deferred change queue is a core service; modules only declare `writable_fields`.

## 7. The shared equipment catalog

### 7.1 Where it lives: its own foundation module, `catalog` [R-7]

Not core, because the catalog is domain data with its own curation UI, its own sources, and its own
classification queue. Keeping it out keeps the core free of domain words. It is a module that SBIS
and TIVS `require`. It offers seams `catalog.items` (lookup, resolve an identifier or token, walk
classification) and `catalog.observe` (record an unclassified observation), and the link kind
`catalog.item`. It is built before SBIS is ported (phase 6).

### 7.2 Shape (from `rmi-sbis-extract/docs/CATALOG_ENTRY_SPEC.md`, `PART_JSON_MODEL.md`)

- **Item**: the identity of one real thing. `id`, `domain`, `classification` path, `status`
  (`classified | unclassified | merged(into)`), and identity attributes validated by the domain's
  attribute schema (a relay has `coil_ohms`, `contact_arrangement`, `polarity`, `release`; a switch
  machine has `model`, `drive`; a stand has `stand_type`).
- **Identifier** (many per item): `value`, `issuer`, `kind` (`mfr_part_no`, `rr_part_no`,
  `catalogue_no`, `stock_no`, `gis_code`, `legacy_sbis_id`, …), `source`, `valid_era`. **All forms
  kept**, including the compound strings from the old table, stored raw beside their split parts.
  An identifier is unique per `(issuer, kind, value)`, never globally.
- **Relation**: `plugs_into`, `equivalent_to`, `part_of(qty)`.
- **Claim**: per-attribute source and confidence (`stated | confirmed | high | high_default | …`),
  so a later correction propagates (the extract project's governing rule).
- **Token map**: generalises `sbis.component_token_map` (`sbis/models.py:ComponentTokenMap`:
  family + casefolded token → item, NULL = deliberate "no equipment"). GIS coded values and grammar
  tokens resolve through it; an unmapped token queues, never defaults.
- **Prices are not catalog data.** They stay with the consumers, keyed by item id: SBIS project cost
  lists and TIVS cost books. The catalog says what a thing is, not what it costs on a project.
  SBIS's `designator` (internal, external or labor, #1045) is a pricing attribute and stays in SBIS;
  labor lines point at items in a `service` domain.

### 7.3 Domains

| domain | seeds | consumers |
|---|---|---|
| `signal.relay`, `.timer`, `.rectifier`, `.battery`, `.charger`, `.transformer`, `.wiu`, `.comms`, `.track_interface`, `.logic_controller`, `.crossing_controller` | `rmi-sbis-extract/conf/dictionary/*` (569 identifier rows), SBIS `equipment_catalog` (503 rows) | SBIS contents |
| `signal.head`, `.mast`, `.bridge`, `.cantilever` (ADR 0018 components) | SBIS external catalog + token maps | SBIS structures, TIVS `signal_structure` |
| `crossing.gate`, `.flasher`, `.cantilever`, `.predictor` | SBIS crossing tokens | SBIS, TIVS `xing_equipment` |
| `track.switch_stand`, `.switch_machine`, `.derail`, `.esl`, `.scc`, `.switch_heater`, `.frog`, `.point` | GIS domains `rmi_trk_stand_type` (HAND/POWER/DUAL), `rmi_trk_drl_type` (SLD/HNG/SWP/OTH), `esl_type` on turnout/derail layers (`rmigis-pyt/templates/trk_impr_domains.yaml`, `track_impr/*`) | TIVS `turnout`, `derail`, `turnout_complex`; SBIS external assets |
| `wayside.detector` | `wayside_det_eq_tbl`, domain `rmi_trk_wayside_equip` | TIVS `wayside_detector` |
| `site.generator`, `.tank`, `.lubricator`, `.house` | GIS domains | TIVS |
| `service` | SBIS labor rows | SBIS pricing |
| `other` | — | anyone (§7.4) |

**How GIS domains map.** A GIS coded value is an identifier with `issuer = "rmigis:<domain>"`,
`kind = gis_code`. Usually it names a *class* (`POWER` stand) rather than a part number, so it maps
to a classification node, and an item is attached when the model is known. Coded values that bundle
data (#908 `120g_v`) decode through the dataset contract first. **How TIVS asset types map.** TIVS
*processes* (`turnout`, `derail`, `signal_structure`, …; `tivs/assets/registry.py:PROCESSES`) stay
code-owned valuation processes (ADR 0009). Their component lines (stand, machine, heater, head)
reference catalog items or classes, and a process never owns a vocabulary of its own.

### 7.4 "Other / unclassified"

Anyone may record a thing the catalog does not know, from SBIS's inventory form, a TIVS finding,
an evidence import or an extraction run. That creates an item with `status=unclassified`, in the
nearest domain it is known to belong to (or `other`). The item carries the **raw text exactly as
recorded**, who, when, where (`Ref`) and the source document. References point at it like any item.
Classifying it later is one of two acts, both audited, both reversible:

- **classify**: set the domain, path and attributes;
- **merge**: point the item at an existing canonical item. The unclassified item becomes
  `merged(into)`, keeps its raw text and identifiers as aliases, and every reference resolves
  through the redirect.

Nothing is deleted, and a curation page shows the unclassified queue by domain and frequency. The
old `Other` and `*MULTIPLE UNKNOWN*` placeholder rows (`CATALOG_ENTRY_SPEC.md` §8) migrate into this
path.

### 7.5 Migration from `sbis.equipment_catalog`

1. Load the extract project's part files and dictionaries as `classified` items with claims.
2. For each of the 503 old rows, run the extract project's loader mapping (old row → one or more
   items; e.g. row 115 "ACSP/DCSP" → 4 parts). Every old row becomes an identifier
   `legacy_sbis_id=<id>`, and its `display_name`, `part_number`, `mfg_part_number` and
   `rr_ref_number` are kept raw and split.
3. Rows that do not resolve become `unclassified` items holding their original text: nothing is
   lost, and the 27 manufacturer part numbers the extract project resolved are attached as claims
   with their sources.
4. Instance rows re-point through a mapping table. Uniqueness on `(bungalow, item)` is dropped in
   favour of `(bungalow, item, confidence)` (extract inventory, "data contract").
5. Prices re-key to item ids. A one-to-many split row is flagged for engineer review, never
   auto-divided.

The loader is tested on the extract project's fixtures (`fixtures/sbis/`), not production data. The
real run is the operator's, at cutover.

## 8. How the modules map onto it

| module | owns | offers | consumes | unbuilt work placed |
|---|---|---|---|---|
| **catalog** (new) | items, identifiers, claims, token maps | `catalog.items`, `catalog.observe`, link `catalog.item` | `reference.entry` (uses, later) | extract loader, curation queue |
| **CIV** | bookmarks, frame cache, markers, Survey123 bindings (`civ/settings.py`) | card `civ.pano`, relation feature → frames, link `civ.frame` | OID dataset (required), marker datasets (read) | frames API from synced `oid` rows (#1982), signed-cookie tiles (#1980), embeddable card and pinned view (#1232/#1233), conversation anchor on `oid:` refs (#1439, [R-8]); measurement (#1226-1229) later, GPX values as *extra* attributes, never overwriting Esri camera fields |
| **SBIS** | bungalows, instances, costs, main systems | links `sbis.bungalow`, `sbis.asset`; seam `sbis.priced_inventory` v1 **with provenance**; validation | `catalog.items` (req), `pm.phase` (uses), card `civ.pano` | GlobalID-first from day one (#1061); unlink (#1950); structure/crossing decomposition cutover (#718/#723) when priced; labor designator (#1045, #1957); detector lump sums (#1990) |
| **TIVS** | runs, snapshots, cost books | links `tivs.asset`; snapshot sealed event; track spans for shell map | `catalog.items` (req), `sbis.priced_inventory` (uses), `pm.phase` (uses), card `civ.pano` | complex trackwork (#410, #1414-1416), `per_slot` instances are free with child rows (#1099), rail quantity basis (#1213, #1373; owner question), provenance into snapshot (#1434) |
| **PM** | properties, phase, parties UI, fee estimates | seam `pm.phase` v1; access-only keys `pmfee`, `pmfin` declared, not in core | parties, QBO (core) | fee estimator rework **after owner scoping** (#1829); estimated-vs-actual calibration (#1301) |
| **CVS** | valuation runs, reference data | none | one dataset, `pm.phase` | port as is; first real contract test ([R-9]) |
| **evidence** (new, later) | third-party sources, pairings, comparisons, decisions | relation bungalow → audit comparison | `sbis.bungalow` link kind, `catalog.observe` | UP audit waves #2000-2004 under ADR 0025; `rmi-sbis-extract` proposals land here, not in SBIS |
| **reference** (later, §8.1) | reference entries | link `reference.entry` | — | not in the build order |

**Not designed, by owner direction:** documents and the durable record (#1298, #601, #1299, tabled
2026-09-18), valuation year (#950, tabled), strip maps (#131), BSIVS (#886). The contract does not
stop any of them being added later as modules.

### 8.1 The reference hub, later

A `reference` module holding documents and notes gathered mostly from free sources, searchable. It
is not designed here. The contract already lets it plug in: it offers the link kind
`reference.entry`; the catalog's claim `source` is a `Ref` *or* plain citation text, so a catalog
built before the hub exists keeps its citations and links them once the hub arrives; SBIS and TIVS
pages show "references" through `links.for_ref` and show nothing while the hub is absent. The
equipment document library measured in `rmi-sbis-extract/docs/EQUIPMENT_DOCUMENT_LIBRARY.md`
(covering 270 of 503 catalog rows by filename alone) is the obvious first content. It is reference
material, not project records, so the tabling of #1298 does not apply.

## 9. The carried-forward decisions

### 9.1 GIS writes: attribute updates only, deferred queue with old-value guard — **stands**

Nothing in the code or issues argues against it. ADR 0016 §4 says the same, adding that write-back
is a user-explicit permission beyond editor role. The issues add the parts the queue needs
(#1220-1225): a **pending-change overlay** on reads, so the platform shows the queued value marked
pending; per-module `writable_fields` allowlists (the manifest); the capability `gis.write_back`
(declared today in `access/models.py:68` with no consumer); **dry-run**; a **conflict-rate halt** and
size caps; **per-field approval**; and **rollback by inverse change**, which is itself a queued
attribute update with the same guard. Queue row: `(dataset, GlobalID, field, old, new, who, when,
reason, status)`. There are no geometry changes, adds or deletes; feature lifecycle stays in the
GIS. It is built last (phase 10), because every other phase works without it. One candidate first
use: the `rel_*` backfill (#1002), where SBIS knows 861 links that match at 99.8%.

### 9.2 TIVS snapshots what persists with a valuation — **stands, extended**

`TivsValSnapshot` already stamps `data_basis` per source run and `platform_version`/`git_sha`
(`tivs/valuation/models.py:42-70`). Extend the snapshot to include (a) the provenance of every
seam value it used (SBIS price source, `as_of`, completeness; #1434), (b) the normalised child rows
and resolved edges rather than slot positions, and (c) the catalog item ids *and* their raw
identifiers as they were at capture. Report time reads only the snapshot. The comparison "does this
still reflect the inventory?" stays a comparison of stamps.

### 9.3 CIV is built on the OID as catalog; only the viewer is third-party — **stands**

The OID layers are the one dataset class declared OBJECTID-keyed (ADR 0023 amendment). The frames
API (#1982) completes the decision: the browser stops querying the feature service live and reads
frames from the synced `oid` rows. Photo Sphere Viewer and the ArcGIS Maps SDK stay the only
third-party parts, and tiles follow `rmi-imagery-tiling`'s `tile-contract.v1.json` unchanged. What
the rebuild does not settle is whether the **standalone viewer** (#1981) is a separate deployable
with its own OAuth; see [R-8].

### 9.4 Fee estimator rules are configurable, with overrides and justification; effort in days — **stands**

The design already follows it: `SPEC.md` §5 enters and displays days and stores hours (l.46, 76),
seed data is editable defaults (`pm/fee/data/seed/`), and override category and note live on the
line (l.333). The owner's #1829 ("not working well in practice") is about fit, not about this rule.
The first step it names, rebuilding 26-100 beside the workbook, is the right one. The rebuild
therefore ports the engine unchanged, lifts "override with reason" into a core settings primitive
(SBIS costs, TIVS cost layer and PM fees keep three private copies today, `seams.md` §5), and waits
for the owner's scope before changing behaviour. The six calibration cases (`docs/planning/pm/
fee-estimate/cases/`) become regression fixtures whose deltas are reported, not asserted.

## 10. Build order

Each phase ends with green CI and a short journal entry, and is small enough for `coder`-tier
tasks except where marked. No phase uses production data. The live platform keeps running
throughout; cutover is a separate operator decision.

1. **Harness and contract.** Repo skeleton, uv workspace, pinned async test harness, CI (ruff,
   pyright, pytest, file-size cap, migrations from scratch, "module PR touches no core" check),
   `MAP.md`. Manifest model, entry-point loader, one `app.py`/`worker.py`, `describe` endpoint and
   CLI, `modules/_template` + `hello` module + `test_contract.py`, decision store with the imported
   index. *(heavy for the contract, coder for the rest)*
2. **Core services.** Identity (dev identity, Portal OAuth port), access with module-declared
   facets and keys, projects, audit, settings with override-with-reason, kit shell, link registry,
   seam registry, card slots, events, jobs. Each gets its own tests; `hello` exercises each.
3. **GIS sync engine.** Port the landing, refuse-empty guard, freeze and freshness; add dataset
   contracts (envelope from `FieldInfo`, slot groups, edges, derived, expectations, decode), drift
   check, `Presence`. Tested on recorded fixture responses and synthetic layers.
4. **CVS port** (if in scope, [R-9]): the first real module through the contract; `pm.phase`
   stubbed via `uses`.
5. **CIV port.** OID frames API, markers via relations, `civ.pano` card with host grant, tiles
   contract.
6. **Catalog module.** Model, domains, unclassified path, token maps, curation page, extract-project
   loader, migration script from `equipment_catalog` tested on fixtures.
7. **SBIS port** on the catalog: GlobalID-first, stored links with unlink, `sbis.priced_inventory`
   v1 with provenance, validation, CIV card hosted.
8. **TIVS port.** Seam consumer per feature, child-row consumption replacing positional rules,
   snapshot extension (§9.2). Calculation code moved as is, with its tests.
9. **PM port** (phase seam, properties, parties UI, QBO), with the fee engine ported unchanged and
   calibration fixtures. Fee rework as its own planned tasks after owner scoping.
10. **Write-back** (§9.1), then the **evidence** module (UP audit waves).

After these: cutover planning (data migration scripts per module, run by the operator against a
restore copy), restricted client access (#261, #437), archive capsule hook (#455, #1423), the
reference hub (§8.1).

**Ops, as design constraints for every phase** [R-10]: config separate from secrets and re-read
on auth failure (#1394), tag-triggered deploy with approval (#1401), private DB (#1403), a restore
proven by drill (#1400, #1424). These are built at cutover, not before; the repo only keeps them
possible (one image, `migrate` runs every chain from manifests).

## 11. Risks

1. **The rebuild never catches up.** The live platform keeps shipping (issues opened daily). The
   mitigations: port rather than rewrite calc code, move byte-identically, and keep a
   `docs/PARITY.md` listing live issues closed after the port snapshot so they can be replayed.
   If phase 8 slips badly, [R-1]'s alternative (evolve in place, carrying over the contract) is
   still open because the contract is designed to be portable.
2. **Data migration at cutover.** GlobalID-first SBIS, the catalog re-key and child rows all
   change stored shapes. Scripts are tested only on fixtures here, because this box has no
   production data. The operator runs them on a restore copy first. The largest uncertainties are
   SBIS rows with no GlobalID and catalog rows that split.
3. **Small-model builders.** 8k/16k-context models misjudge cross-cutting changes. Mitigations:
   the 500-line cap, the one-layout rule, contract tests, and heavy-tier review at the end of each
   phase.
4. **Catalog granularity is open.** Assembly vs module (GCP 4000), battery as part vs attributes,
   GIS codes as class vs part (`rmi-sbis-extract.md`, "open questions"). The model supports both
   answers (`part_of` relations, class nodes), but pricing grain waits on the owner.
5. **The CIV card cut** changes access behaviour if done carelessly. `grant="host"` must reproduce
   today's behaviour exactly, and a test pins it.
6. **Budget.** Heavy-tier work is limited to the contract (phase 1) and reviews. Everything else is
   standard or local.
7. **Owner questions gate parts of phases 7–9**: rail quantity basis (#1373), crossing labor grain
   (#809), shrink threshold (#1689), CIV anchor identity (#1439). Tasks that depend on an answer are
   marked blocked, not guessed.
8. **Not verified in this proposal:** live layers against templates, Survey123 field use, runtime
   seam behaviour, the full DTO list of `sbis.seam` (all noted as unverified in the inventories).

## 12. For the operator to rule on

| # | recommendation |
|---|---|
| R-1 | New repo; new core and contract; modules **ported**, not rewritten. The alternative (evolve in place) is viable and cheaper. |
| R-2 | One decision store (`docs/decisions/` with status front matter); ADRs and `OWNER_RULINGS.md` imported as history. |
| R-3 | GlobalID is the only foreign key for GIS features; OBJECTID only for datasets declared so (OID); Asset ID display-only. |
| R-4 | Typed absence (`Presence`) as a core vocabulary used everywhere a count or value can be missing. |
| R-5 | Every value that crosses a seam carries provenance (`source, as_of, completeness`); consumers snapshot it. |
| R-6 | Slot groups normalised to child rows on sync; new layers use related tables; old layers are not migrated. |
| R-7 | The catalog is its own foundation module that SBIS and TIVS require, holding no prices. |
| R-8 | Is the standalone CIV viewer (#1981) a separate deployable? Proposed: the same image in a CIV-only mode, deferred with client identity (#261). CIV conversation anchor on `oid:` refs. |
| R-9 | CVS is in scope, ported as is, and used as the first real contract test. |
| R-10 | Ops items are constraints now and work at cutover. |
| — | Tabled items stay tabled; the reference hub is a later module; fee rework waits for the owner's scope (#1829). |
