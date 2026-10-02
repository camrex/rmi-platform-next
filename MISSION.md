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
