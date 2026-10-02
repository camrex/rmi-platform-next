# MISSION — rmi-platform, rebuilt

The operator's brief, 2026-09-29, in his words and then as working rules. Read this first,
every run. It changes only when the operator changes it.

## What he asked for

> Take rmi-platform and make it better, without me driving it interactively. Rebuild it from
> scratch. More modular, almost like plugins, with links between plugins when they exist. LLM
> friendly. rmi-platform on steroids. Take our existing GIS schemas and find ways to make them
> better and more efficient. Without me telling it what to do, take what we have and figure it
> out. Look at the other projects we have been working on and see if there is anything useful,
> especially rmi-sbis-extract. Completely hands-off, working in the background, no timeline,
> and it must not run up a bill.

## What rmi-platform is today (read the code; this is orientation, not a spec)

- RMI Valuation's internal web platform: FastAPI, HTMX, Jinja2, PostgreSQL. Railroad corridor
  appraisal and GIS work for a small firm.
- Modules: **SBIS** (signal bungalow equipment inventory), **CIV** (Corridor Imagery Viewer:
  360 imagery with Photo Sphere Viewer and the ArcGIS Maps SDK, built on the Oriented Imagery
  Dataset as its spatial backbone, with virtual inspection through Survey123), **TIVS 2.0**
  (track improvement valuation), and a planned **PM** module whose first feature is fee
  estimating (a written spec exists in the repo).
- GIS is read-only today: one-way sync from the ArcGIS Enterprise Portal feature services into
  the platform's own database.

## Decisions already made — carry them forward unless you can show they are wrong

- GIS writes, if any, are **attribute updates only**, through a deferred change queue (dataset,
  GUID, old value, new value, who, when; applied only if the old value still matches). Never
  geometry, adds or deletes: feature lifecycle stays in the GIS.
- TIVS **snapshots** the data that persists with a valuation; it does not read GIS live at
  report time.
- CIV is built on the OID as the catalog; only the viewer itself is third-party.
- The fee-estimate module's rules are **configurable, with overrides and captured
  justification**, not hardcoded, and effort is shown in days.

If you conclude one of these is wrong, say so in the architecture proposal with the evidence.
Do not quietly design around it.

## Operator direction, 2026-09-29 evening (after the issues digest) — read before 0.7

In his words, lightly trimmed:

> One thing I am thinking as being more modular is an easier ability to add in modules, and
> its connection into rmi-platform, as well as seams between modules.
>
> [rmi-sbis-extract carries] a new catalog system. One idea is that we expand the catalog
> beyond SBIS and also cover TIVS. This would include having domains for stands, switch
> machines, derails, etc., with a well defined catalog (to be honest, the possibilities are
> finite, but that doesn't mean we don't run across something new, so we also need the
> ability to have an "other" to be added into the system later).
>
> The other idea: we are amassing a lot of information, documents, etc., that could become a
> resource in its own right, which could be separate (a module), that could not only be useful
> for TIVS, SBIS, etc., but could be its own useful web information hub (most of it pulled from
> freely available sources, amassed in a single location). This is a separate project, and not
> an immediate need, but would be useful, even internally: right now I have to remember where
> to find things.

What this asks of the architecture proposal:

1. **Adding a module is the measure of modularity.** Show concretely what it takes to add a
   new module: what it declares, how it connects to the core, and how it offers and consumes
   links and seams to other modules. Make that path short, documented and testable (a module
   template or checklist a new session can follow). The seams between modules are first-class,
   typed and versioned, not incidental imports.
2. **A shared equipment catalog, beyond SBIS.** Treat the catalog from `rmi-sbis-extract`
   (docs/inventory/rmi-sbis-extract.md) as the seed of a platform-wide catalog that SBIS and
   TIVS both consume: signal equipment today, and track-side domains such as switch stands,
   switch machines and derails. Well-defined domains, one canonical entry per real item, all
   identifier forms kept, and an explicit **"other / unclassified"** path so something new can
   be recorded now and classified into the catalog later without losing what was recorded.
   Say where it lives (core service or its own module), how the GIS domains (docs/inventory/
   gis-schemas.md) and the TIVS asset types map onto it, and what the migration from today's
   SBIS `equipment_catalog` looks like.
3. **A reference / knowledge hub, later, as its own module.** Documents and information
   gathered mostly from freely available sources, in one place, searchable, useful to SBIS and
   TIVS and possibly on its own. **Do not design it in detail or put it in the build order's
   early phases.** Make sure the module contract and the linking model would let it plug in
   later (other modules linking to reference entries; the catalog citing its sources there).
   Note that the owner has tabled the *project documents* arc (#1298, #601, #1299); this hub is
   a different thing (reference material, not project records) and is not tabled, only later.

The digest's other questions (rebuild vs evolve, one decision store, GlobalID as the only key,
typed absence, provenance across seams, related tables vs slots, tabled items, the fee
estimator, ops) are not yet answered by the operator. Where the proposal takes a position on
them, mark it as a recommendation for the operator to rule on at the checkpoint.

## Operator direction, 2026-10-02 — pricing is its own module (revise the proposal, task 0.8)

After reading PROPOSAL.md, the operator agreed that prices are not catalog data, but not that
they stay inside SBIS and TIVS: "I'm almost thinking that Costs/Pricing may become its own
module." His answers to the questions that decide it:

- **Do prices carry from one project to the next?** "Sometimes, and often they are a good
  starting point."
- **Are costs brought to a valuation date with cost indexes?** "Yes, in fact sometimes the only
  available costs might be a 2019 signal catalog, or an estimate from a prior year."
- **Where do prices come from?** "It's a mix, all of the above and more" (engineers' estimates,
  vendor quotes, published catalogs and estimator's guides, railroad price lists, prior
  estimates, and others).
- **And:** "The other thing this might help is user permissions."

What this asks of the revised proposal:

1. **A `pricing` module between the catalog and its consumers**: catalog (what a thing is) ->
   pricing (what it costs, per source, date and scope) -> SBIS and TIVS (which use prices to
   produce estimates and valuations). It `requires` the catalog; SBIS and TIVS `require` pricing.
2. **It holds the cost basis, and only that.** A price record is keyed to a catalog item *or a
   classification node* (a class such as a POWER switch stand, when the model is unknown), with
   material and labor kept apart, units, the source (a typed source kind plus citation, open to
   new kinds), the cost's own basis date, and a scope: general, railroad/client, project. A
   project may start from prices carried over from earlier projects or from general sources and
   override them, with the core's override-with-reason primitive. Nothing is overwritten; a
   superseded price stays readable.
3. **Escalation is part of pricing.** Cost indexes (series, source, values by period) and the
   act of bringing a price from its basis date to a valuation date, recorded as a provenance
   chain the reader can see: "2019 vendor catalog, trended by <index> to 2026-06". An old
   catalog or a prior-year estimate is often the only source; the design must treat that as
   normal, not an edge case.
4. **Valuation logic stays in the modules.** Extended cost, indirects, depreciation and survivor
   curves, and rules such as "an unpriced labor line poisons the labor leg" (OWNER_RULINGS
   2026-09-25) remain in SBIS and TIVS. Pricing answers "what does this cost, per this source, at
   this scope, as of this date"; it never values an inventory. PM fee billing rates are a
   different kind of number and stay in PM.
5. **Seams carry price references, not copies.** SBIS still produces the engineers' pre-indirect
   bungalow estimate and only the (material, labor) pair crosses to TIVS (existing rulings), but
   each value references the price records it used, so provenance travels by reference (#1434)
   and the TIVS snapshot freezes exactly which prices, sources and index values it used (§9.2).
   Items priced on both sides today (signal structures, crossing equipment, switch machines;
   §7.3) are priced once; say how double pricing (#952) becomes impossible by construction.
6. **Permissions are a reason for the module, so design them.** Who may view prices, who may
   enter or override them, who may see a given source (a railroad's price list may be
   confidential to that client's projects), and that restricted client principals (#261) see no
   cost basis unless granted. Declared through the module contract (facets and capabilities).
7. **Revise in place**: §7.2 (the "prices are not catalog data" bullet), §8 (module map), §9.2
   (snapshot), §10 (build order: pricing between catalog and the SBIS port), §11 (risks: pricing
   grain, migration of SBIS cost lists and TIVS cost books into price records), §12 (R-7 split
   into catalog and pricing rulings). Keep the rest of the document as it is. Under 12 pages still.

## Operator direction, 2026-10-02 — TIVS asset types are sub-modules (also task 0.8)

The operator: "we may want to consider whether assets in TIVS should be treated as
sub-modules", then, on turnouts and complex trackwork:

> - Turnouts: Source: turnouts_cx, Filter: to_complex_type: NML
> - Complex Trackwork: Source: turnouts_cx, Filter: to_complex_type: not NML
>
> If we ever wanted to split Complex Trackwork up into its different types, which is probably
> best at some point, this would make it easy. [On rail netting out turnout-excluded feet:] is
> that something dependent on another module (turnouts), or the source GIS data? I would argue
> that what Rail needs is its primary source and any source it relies on, not necessarily a
> cross module thing.

What this asks of the revised proposal:

1. **TIVS is a valuation framework; each asset type is a sub-module.** The framework owns runs,
   the five stages (ADR 0009), readiness gates (ADR 0024), the snapshot and reports. An asset
   sub-module is one folder declaring: its **primary source and filter** (dataset + predicate,
   e.g. `turnouts_cx where to_complex_type = 'NML'`), any **secondary sources** it reads, its
   components and the catalog classes they are, the prices it asks pricing for, its RCN and
   depreciation rules, its exhibit, and its test fixtures. Calculation stays code (ADR 0009).
   Registered with TIVS in the same declarative style as the platform manifest, not with the
   core: no routes, nav or migration chain per asset type; shared run/asset tables with a
   per-asset declared detail schema.
2. **Sub-modules depend on data, never on each other.** Rail depends on its primary source
   (track) and secondary sources (`turnouts_cx`), not on the Turnout sub-module. A turnout's
   **excluded length** is a property of the turnout class in the **catalog** (as a relay's coil
   resistance is). The operator, 2026-10-02: "In reality Turnouts never rely on this excluded
   length, it is just a property of the turnout." Rail reads it from the catalog through the
   turnout records' class (#1414, #1373). Say where each such fact lives; the default home for
   a property of a kind of thing is the catalog.
3. **Every record lands in exactly one asset type.** The framework checks, per source, that the
   sub-module filters are disjoint and exhaustive; a record no filter claims is reported as
   `unassigned` (typed absence), one claimed twice fails the run. This is what makes splitting
   Complex Trackwork into DSLIP, LAP_SW, TO_MPF, DIA_MPF (#410) safe: add a sub-module with a
   narrower filter, and the general complex-trackwork filter becomes "not NML and not claimed".
   Open question for the operator (mark it): is an empty `to_complex_type` a normal turnout or
   undecided?
4. **Revise in place**: §8 (TIVS row), §9.2 (snapshot records which sub-module and filter
   valued each record), §10 (phase 8: framework first, then asset sub-modules one at a time,
   turnout and complex trackwork as the worked example), §11 (risk: filter coverage on
   era-mixed data such as the Schema-1/Schema-2 turnout and wayside pairs), §12 (a ruling line).

## Operator direction, 2026-10-02 — track inventory on domains, free text only as the exception (also task 0.8)

> [It] goes to the need to as much as possible start basing the actual inventory of track
> improvements on not free text but domains. And only allow free text when you aren't sure or
> it is new. Where you could indicate "Other" or "TBD" in the domain and a free text to either
> describe or name if new.

What this asks of the revised proposal:

1. **One capture pattern for inventory fields**: a coded domain value, with two reserved codes,
   **`OTH`** (it is something the domain does not list yet) and **`TBD`** (not determined), and
   a companion free-text field used only with them, to name or describe the thing. Free text is
   the deliberate, countable exception, never the default.
2. **It maps onto what the proposal already has**: a domain value resolves to a catalog class;
   `TBD` is typed absence `undecided` (§6.1); `OTH` + text is the catalog's unclassified path
   (§7.4): kept verbatim, queued by frequency, later classified or merged, with every reference
   following. Domain codes are catalog identifiers (`issuer = rmigis:<domain>`, §7.3), so the
   GIS domains and the catalog stay one vocabulary, and adding a new code to a domain means
   adding (or classifying into) a catalog entry.
3. **For the GIS side, as proposals** (the Portal is not assumed to change, MISSION): the
   standard for new and revised track-improvement layers and Survey123 forms is domain +
   `OTH`/`TBD` + companion text; existing free-text and slot fields keep being read through the
   catalog's token map and dataset contracts, with unmapped text queued, never defaulted.
   Cross-reference docs/inventory/gis-schema-review.md where it already proposes domains.
4. **Revise in place**: §6.2 (dataset contracts: reserved codes and companion text), §7.3/§7.4
   (domains as catalog identifiers; `OTH` feeds the unclassified queue), and a line in §12.

## Operator direction, 2026-10-02 — who defines, requires and enforces catalog properties (also task 0.8)

Asked whether a required catalog property such as a turnout's excluded length is defined by the
catalog, by TIVS, or by the Rail (and Ties) sub-module, the rule agreed is:

1. **The catalog defines a property**: name, type, unit and meaning, in the domain's attribute
   schema (§7.2). A module that needs a new property gets it added to the catalog domain; no
   module attaches private properties to catalog entries.
2. **A consumer requires it, for its own use.** "Required" belongs to a use, not to the property:
   Rail (and Ties) declares that every turnout class in its secondary source must have
   `excluded_length`; Turnout and SBIS do not need it. The catalog itself never makes such a
   property mandatory, so a new thing can still be recorded as `OTH`/`TBD` before it is known.
3. **The TIVS framework enforces it at the readiness gate** (ADR 0024): a Rail run is blocked,
   naming the classes that lack the property, rather than valuing with a silent zero or a
   default footprint (#1414). The same gaps appear in the catalog's curation queue as
   "properties wanted by <consumer>". Pricing follows the same rule: sub-modules declare which
   classes they need priced, and the gate reports what is missing.

**One standard, not per railroad.** The operator, 2026-10-02: "We don't differentiate between
railroads. We use as close to a single standard (source) that we can independent of railroad.
And in reality, what is the real difference? Plus, let's take into consideration that Union
Pacific and Norfolk Southern may merge soon, who's standard would be right if they differ? The
fact is that its not like UP will go out and replace all of the turnouts with their standard."
So a catalog class carries one value per property, from RMI's chosen standard source, recorded
as a sourced claim (source, confidence). No per-railroad variants of a class or property.

**Revise in place**: §7.2 (attribute schemas; properties defined only by the catalog; claims
carry the standard source), §7.3 (track.turnout properties, excluded_length as the example), the
TIVS framework text (sub-modules declare required properties and prices; readiness gate
enforces), and §12.

## Operator direction, 2026-10-02 — review of the proposal: what else 0.8 must cover

A full review of PROPOSAL.md against the inventories found it sound and specific; these are the
gaps. The operator agreed to items 1–7 and asked for the rest to be handled as below.

1. **Vocabulary authority.** For equipment vocabularies the **catalog is the authority**, not the
   GIS domain YAML. Classifying an `OTH` creates a catalog class that then needs a code in the GIS
   domain and the Survey123 choice list. The catalog exports domain definitions for `rmigis-pyt`,
   and the GIS admin applies them with its existing domain-sync tool (a schema change by an
   admin, not a feature write, so it does not touch "GIS writes are attribute-only"). Design that
   loop; otherwise there are two vocabularies that drift.
2. **A valuation (as-of) date** on every TIVS run, frozen in the snapshot. Pricing escalation needs
   it. This does not reopen #950 (valuation year in PM, tabled); the run carries its own date.
3. **Units.** A small core vocabulary for quantities with units, used by catalog properties,
   pricing and TIVS, so a per-track-foot price cannot meet a count of turnouts (#1213 is a units
   bug).
4. **Correction:** drop the proposed SBIS uniqueness `(bungalow, item, confidence)`; it lets one
   relay count twice. One row per item per bungalow with a quantity; confidence lives on the
   claims (evidence) behind it.
5. **Pricing seed sources:** the **2019 Alstom Estimator's Guide** already in `rmi-sbis-extract`
   and today's TIVS cost books, both as general sources with their basis years and escalation;
   the cost books migrate into price records.
6. **Port vs restructure:** port TIVS calculation functions unchanged; change only the adapters
   that feed them (sub-modules, child rows, pricing). Each asset sub-module's fixtures prove the
   numbers did not move.
7. **When real data arrives:** the build order names the phase at which the operator places
   project 26-150 data in `data/` (before the SBIS and TIVS ports), so the ports are checked
   against a real project before cutover.
8. **Land valuation and sales data: out of scope for now.** The operator: "something that we need
   to address at some point, but for now, I think we leave it as is, though the module could use
   some love." CVS is ported as is (R-9 stands as the first contract test). The real-property
   layers and the corridor sales database (#1302) are not designed. In §8 list, briefly, what
   "some love" for CVS could mean later, from the issues, without putting it in the build order;
   and make sure the contract would let a sales/comparables module plug in later.
9. **The old platform during the rebuild.** The operator: "We obviously can't stop and wait for
   rmi-platform-next to catch up, we have active projects that need to be completed, and real
   issues that have to be fixed. I think at this point rmi-platform should only address issues
   that have to be fixed to get to a complete valuation. And perhaps we need to make sure that
   rmi-platform documents those." So: rmi-platform takes only changes needed to complete a
   valuation, and each such change is documented where the rebuild can find it. Propose the
   mechanism (recommended: a GitHub label on rmi-platform issues, e.g. `rebuild:replay`, plus a
   "rebuild impact" line on each PR; the issue snapshot already reaches labels) and make
   `docs/PARITY.md` the rebuild's list of those changes, each replayed or marked not needed,
   checked before every module's cutover. Replace risk 1's mitigation with this.
10. **Report production stays out.** The operator: "we still handle report production. That is a
    much later thing ... perhaps a future module." Note it beside the reference hub as a possible
    later module; design nothing; the snapshot is what it would read.
11. **Schema changes need a process.** The operator: "We also need to figure out how to handle
    any proposed schema changes." Design it, for **GIS schema** changes (the Portal layers,
    domains and Survey123 forms; the platform's own database migrations are already handled by
    the per-module Alembic chains): a schema-change proposal record in the decision store (status
    open / ruled / applied), each stating the change, the reasons and issues, its class (P / T / O
    as in gis-schema-review.md), the impact on existing data, Survey123 forms, dataset contracts
    and consumers, and the rollback. The rebuild never edits `rmigis-pyt` (read-only to it): it
    drafts the YAML change as a patch beside the proposal; the operator rules; the GIS admin
    applies it through `rmigis-pyt`. Changes go expand-then-contract: add the new field or domain
    code first, move consumers (dataset contract version bump), retire the old one later. The
    drift check confirms the published layer matches. Catalog-driven domain exports (item 1) are
    one kind of such change.
12. **Diff review first (task 0.7b).** The inventories were written against the source repos as
    of 2026-09-30. Before revising, review what changed since in each source repo and in the
    rmi-platform issues, and carry anything that affects the proposal into 0.8.

## What "better" means here

1. **Modules as plugins.** A small core (auth, config, database, GIS sync, shared UI shell,
   jobs, reporting) and modules that register with it through one explicit contract: their
   routes, models, migrations, permissions, navigation, background jobs, and the **links** they
   offer and consume ("an SBIS bungalow links to its CIV panoramas and its TIVS assets"). A
   module that is absent leaves no broken links.
2. **LLM-friendly.** A new session of any model can find its way in minutes: a short map of
   the code, one obvious place for each kind of thing, typed interfaces, tests that explain
   intent, docs next to code, stable names. Machine-readable descriptions of modules and data
   (so tools and agents can ask the platform what it has) are in scope.
3. **Better GIS schemas.** The 18-feature-class data model and its YAML definitions
   (`rmigis-agp-toolbox`), topology, Survey123 forms: find redundancy, inconsistent types and
   names, missing constraints, and what would make sync, validation and querying simpler.
   Propose; do not assume the Portal changes.
4. **Use what exists.** `rmi-sbis-extract` (signal drawing extraction and the part catalog) is
   the one named. Also `rmigis-pyt` and `rmi-imagery-tiling`.

## Constraints

- **Money.** Your router key has a monthly cloud budget. When it runs out, cloud calls fail
  until it resets: stop and wait. Use the cheapest tier that can do the task well
  (see `AGENTS.md`). Local models are free but small.
- **Data.** No production data unless the operator puts it in `data/`. Never ask for, look
  for or use credentials beyond the ones this box already has.
- **The originals are read-only.** You study the source repositories; you change only this one.
- **One checkpoint.** After discovery, write the architecture proposal and stop. Building
  starts only after the operator approves it (`approvals/`).
- **No timeline.** Small, correct, committed steps beat large ones.
