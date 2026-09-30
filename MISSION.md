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
