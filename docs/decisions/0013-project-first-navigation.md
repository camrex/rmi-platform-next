---
status: ruled
kind: architecture
date: 2026-07-12
refs: []
source_status: "Accepted (2026-07-12) · Amended (2026-08-25)"
imported_from: rmi-platform/docs/adr/0013-project-first-navigation.md
imported_on: 2026-10-03
---
# 0013 — Project-first navigation: picker home, project home, explicit project scope

**Status**: Accepted (2026-07-12) · Amended (2026-08-25)

## Amendment (2026-08-25) — administrative surfaces are portfolio-scoped, and say so

Project-first governs **appraisal** surfaces. An administrative surface is
portfolio-shaped by nature — "what has each engagement billed" is the question,
and answering it one project at a time is the spreadsheet this platform is
replacing. This ADR already concedes the shape once, for `/admin`; what is new
is a cross-project surface gated on a **module grant** rather than a platform
role.

The seam is `require_module_anywhere("<key>")`
([`platform_core/access/deps.py`](../../platform/src/platform_core/access/deps.py)),
built for PM's `/finance` (#1300 slice 6) and deliberately not PM-private: the
Data Management surface of #1156 wants the same shape.

Three properties keep this an amendment rather than an exception:

- **The result set is the scope.** It yields a `PortfolioContext` carrying the
  caller's projects for that module, resolved through the *same*
  enabled-and-granted rule and the same `narrowed_role` the per-project
  dependency applies. A route filters its query by that set and checks nothing
  per row, so the two paths cannot disagree about who reaches what.
- **No project is ever picked.** There is no active project and no fallback —
  clause 4's silent default is not reintroduced by the back door. A portfolio
  route that needs one project asks the context for it by id, and absent means
  not-entitled and not-found at once.
- **An empty set is a 403.** Rendering "no projects" to somebody entitled to
  none still tells them the surface exists, which for a finance overview is
  itself a disclosure.

Entry is from the picker rather than through it: the platform home offers a
link per cross-project surface the caller would actually be admitted to,
resolved by the same call the route's dependency makes. Whether these belong in
the shell nav instead, and what a project card should carry for whom, is a
navigation question this amendment deliberately does not settle.

## Context

The access model has been project-first since ADRs 0002/0005: authorization is per
(user, project, module), and `effective_grants` already yields
`(project_code, module_key)` pairs. Navigation never caught up — it is module-first:

- The platform landing (`platform-web/src/platform_web/home.py`) shows a card per
  module with no project dimension at all.
- Each module then solves project selection on its own: TIVS and CIV built picker
  homes; SBIS has none and silently uses the default.
- The active project rides `?project=<code>` on every URL, and a **missing project
  silently falls back** to `settings.default_project_code` — the "single-project
  phase" convenience (`access/deps.py`, `tokens/deps.py`).

The silent fallback has already produced a real defect class: a bare HTMX post
resolved the default project and **wrote another project's data** (#232) — TIVS
grew `post_url()` purely as a guard against it. Meanwhile three live modules,
growing cross-app functionality (the ADR 0010 bungalow seam, shared GIS
bindings — #141), and an expanding project model (#123: client, railroad,
branding) all want a project-scoped surface that today does not exist.
App-then-project is the wrong grain; the data model has said so all along.

## Decision

Login → pick a project → a project home showing that project's apps. Concretely:

1. **Platform home (`/`) becomes the project picker.** It lists the caller's
   projects from `effective_grants` — code, name, status, and the modules each
   opens. The module-first launcher retires (admin entry stays in the topbar).

2. **A project home lives at `/p/{code}`** (platform-web, path-scoped): project
   identity, module cards filtered to *enabled ∩ granted* for the caller, and the
   durable slot for cross-app surfaces and project management. The #123 fields
   (client, railroad, contacts, …) render here as they land; project logos (#115)
   already exist to brand it.

3. **Project scope on module surfaces stays `?project=<code>` — explicit, never
   ambient, never defaulted.** Two alternatives were considered and rejected:

   - *Path-scoped module URLs* (`/p/{code}/tivs/…`): structurally attractive —
     the scope cannot be forgotten — but once the silent default is retired an
     enforced query parameter provides the same safety, and the migration would
     touch every hand-built, server-generated href/form/data-URL across three
     modules (plus bookmarks and Power Query templates) for no behavior gain.
     Revisit when the design-system track (#143) centralizes chrome and makes
     link generation mechanical; until then this is deliberate deferral, not
     drift.
   - *Session-cookie "active project"*: rejected outright. Deep links must be
     deterministic, two tabs on two projects must not race a cookie, and #232 is
     precisely what ambient project state does to writes.

4. **The silent default retires from production.** `default_project_code`
   survives only where dev identity already does (non-production,
   `settings.is_production` gate); in production a module GET without
   `?project=` redirects to the picker, and unsafe methods, fragments, and
   analytical/PAT requests fail loudly (400) — never a silently chosen project.
   The PAT path (`tokens/deps.py`) drops its fallback the same way: analytical
   pulls always name their project.

5. **Persistent project context in the chrome.** The topbar shows the active
   project and a switcher (back to `/p/{code}` and `/`). Modules render it in
   their own chrome for now — the platform provides the data and URL helpers —
   pending platform-owned chrome under #143.

6. **Module pickers fold into the platform.** With `?project=` present a module
   home is its project-scoped overview; without it, it redirects to the picker.
   TIVS's and CIV's per-module pickers retire; SBIS's missing picker is resolved
   by the same rule instead of a third hand-rolled one.

Admin (`/admin`) stays platform-scoped, unchanged. Delivery is sliced on #241:
this ADR → picker + project home (additive; module URLs keep working) → topbar
context + switcher → retire the default and fold the pickers.

## Consequences

- The #232 defect class dies at the enforcement seam (`require_module_access`),
  not via per-module guards; TIVS's `post_url()` becomes belt-and-braces.
- New users land on their projects — the grain work is actually organized by —
  and cross-app functions finally have a home surface.
- `?project=` remains on every module URL: accepted verbosity; existing deep
  links, bookmarks, and Power Query templates keep working unchanged.
- `default_project_code` leaves production configuration; local development
  keeps the convenience behind the existing non-production gate.
- Slice 4 changes module-home behavior (redirect instead of picker/default) —
  called out in release notes when it ships.
- #123's expanded project model gains its rendering surface before columns are
  added, and #141's bind-once dataset admin gains a natural project-level anchor.
