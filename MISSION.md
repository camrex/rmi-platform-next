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
