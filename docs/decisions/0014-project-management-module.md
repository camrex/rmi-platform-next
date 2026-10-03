---
status: ruled
kind: architecture
date: 2026-07-17
refs: []
source_status: "Accepted (2026-07-17)"
imported_from: rmi-platform/docs/adr/0014-project-management-module.md
imported_on: 2026-10-03
---
# 0014 — Project management: organization/contact registry in core, `pm` module workspace, hub references systems of record

**Status**: Accepted (2026-07-17)

## Amendment (2026-08-15) — PM also owns the data-maturity phase (ADR 0024, #897)

PM grew one table, one workspace control, and one seam — an addition under this
ADR, not a redesign: `pm.project_phase` (one row per project, `project_id`
unique, cross-schema FK out of the ORM as everything else here is), the
`pm.phase` service, the Data phase card on the workspace, and
`phase_for(session, project_id)` as the read other modules take through a
one-file adapter of their own (ADR 0010's `sbis_seam` shape). Property scope,
parties, documents and fee planning are untouched.

The phase — `survey` → `costing` → `valuation` → `delivered`, unset legal — is
**deliberately not** the `lifecycle_stage` this ADR defines, and is not derived
from it. `lifecycle_stage` is the engagement's *business* state; the phase is
how far the *data* has matured, and `analysis` alone spans both costing and
valuation, so no lossless mapping exists in either direction. The two render
side by side on the workspace with different owners: PMs move the stage, and
whoever is doing the data work moves the phase. Authority is plain PM write in
either direction, audited as `pm.phase.update` with `{old, new, note}`; the
confirmation on a backward move is UI only. Rationale and the alternatives
declined are in [ADR 0024](0024-shared-validation-engine.md) and
[VALIDATION_ENGINE_DESIGN.md](../planning/VALIDATION_ENGINE_DESIGN.md) §5.

This is also the first module-side answer to "the workspace admits per-module
engagement summaries via a light provider contract" below: the phase is the
value those summaries will be *read at*.

## Context

The platform is organized project-first (ADR 0013): login → picker → a project home at `/p/{code}` that was explicitly built as "the durable slot for cross-app surfaces and project management." What fills that slot today is thin: the #123 business-identity fields on `platform.project` (`client_name`, `railroad_name`, `railroad_mark`, `location`), project logos, and module cards. Issue #262 asks for the project-management layer that turns the page from a launcher into a workspace.

Three forces shape the design:

1. **The string fields are already showing their limits.** `client_name` is one free-typed string per project — but a valuation project involves *several* organizations of the same kind playing different roles (client, property owner, subject railroad, contractors), the same organization recurs across projects under drifting spellings, and the person to call at a client differs per project. Exhibit letterhead white-labeling (#134's `letterhead: client` variant) and deliverable addressing need structured parties, not strings.
2. **Restricted client login (#261) is anticipated.** A client login must hang off a durable person record, and clients reaching the project home must not see internal PM material. Where the party data lives and where the module fence sits are security decisions, not conveniences.
3. **Systems of record already exist.** SharePoint holds full document storage; QuickBooks Online (QBO) owns billing, time tracking, and invoicing. Rebuilding either inside the platform would be a maintenance liability and a data-integrity hazard.

## Decision

### Two governing principles

1. **Platform-core owns what other modules consume; modules own domain surfaces.** The same split that governs projects, users, GIS bindings, and the documents engine applies here: the organization/contact registry is cross-module identity and lands in `platform_core`; the workspace UX and PM-sensitive domain land in a module.
2. **The hub references systems of record; it does not replace them.** SharePoint remains the system of record for document storage; QBO remains the system of record for billing, time, and invoicing. The platform links out. The standing test for any future feature request: *if a system of record already exists, the platform references it rather than absorbing it.*

### Party registry (platform-core)

A registry of organizations and people, in the `platform` schema, replacing role-baked "client manager" framing:

- **Organization** — a reusable company record. Client, property owner, railroad, and contractor are all Organizations; *role is not baked into the record*. Fields (all optional beyond `name`): `name`, `reporting_mark` (AAR mark, the railroad natural key), `website`, `notes`, `is_active`, and a structured-lite address (`address_line1`, `address_line2`, `city`, `state`, `postal_code`) — one address per organization in v1; distinct billing-vs-physical addresses are the recorded trigger for promoting to an address entity, not built now. **Dedup is a continuous concern, not a backfill one**: only railroads have a natural key, and in-app creation will accumulate near-duplicates ("First National Bank" / "First Natl Bank"). Two defenses are part of the design: the org/contact picker **searches and offers existing records before allowing new** (Wave 2 UX contract), and the registry service provides a **merge/redirect operation** (re-point role rows and contacts to the survivor, deactivate the duplicate — audited). Merge must **de-collide, not blindly re-point**: when duplicate and survivor are both parties on the same project, the redundant `(project, role)` rows are dropped and client primacy resolved — otherwise the primary-client unique index fails the transaction at runtime. This keeps the problem the backfill pays a human to fix once fixable forever after.
- **Contact** — a person, belonging to an Organization; reusable across projects. Fields: `name` (single display name), `title`, `email`, `phone`, `notes`, `is_active`, an optional address of the same structured-lite shape, and a nullable one-to-one `user_id` → `platform.user` (see *Contacts vs. users* below). A contact with no address of its own **assumes the organization's** — a resolution rule in the service/display layer, never a copied value, so an organization address change propagates to every contact that has not overridden it.
- **PartyRole** — roles are **reference data, not migration constants**, in two scoped lists (`organization` roles, `contact` roles). Each list ships seeded **well-known entries with stable keys** that code may reference and the app protects from rename/delete — organization: `client`, `railroad`, `property_owner`, `equity_owner`, `contractor`; contact: `primary`, `billing`, `appraiser`, `project_manager`. Two ownership roles exist because they name **different relationships**, and each label states its referent: `property_owner` *owns the appraised property* (an org-to-project fact), while `equity_owner` *holds a stake in the property-owning entity* (NS and CSX each own a piece of Pan Am Southern). A bare `owner` role was seeded initially and dropped — it hid which of the two was meant. Join rows store the stable string `role_key` (the party-role natural key), never a seeded surrogate id — database constraints and code reference the key, so nothing depends on environment-specific ids. Beyond those, **new roles are added in-app** (from the `pm` workspace, write-gated): real engagements surface parties whose role is known informally long before it fits a fixed vocabulary, for organizations and people alike. Code never branches on a user-created role — they are descriptive only.
- **ProjectOrganization** — the join carrying **roles per project**: one row per (organization, role). Both directions are many: one organization holds multiple roles on a project, and multiple organizations may hold the *same* role — including `client` (co-clients happen; exactly one client row per project is flagged `is_primary` for billing/letterhead, enforced by a partial unique index whose predicate names both conditions — `WHERE role_key = 'client' AND is_primary` — so a stray `is_primary` on a non-client row cannot dodge the constraint). The motivating shape: Pan Am Southern as `railroad` *and* `property_owner`, Norfolk Southern as `client` *and* `equity_owner`, CSX as `equity_owner` — three organizations, five role rows, on one project. Equity rows carry a nullable **`ownership_pct`** (RMI allocates appraised value by stake) — deliberately unconstrained beyond nullability: recorded stakes need not sum to 100 (untracked minority holders, incomplete information), a conscious non-constraint rather than a missing validation. The percentage is **project-scoped by design, not a global fact**: a valuation is a point-in-time snapshot, JV stakes change, and a mutable global graph would silently restate historical appraisals the moment a JV re-capped — pinning the split to the engagement is the correct model, not a scope dodge. Still deliberately **not** modeled: a general org-to-org ownership graph. An `equity_owner` row implicitly means "a stake in *the* property owner," unambiguous while a project has one property-owning entity (the v1 assumption); a project with two property owners is the recorded trigger for equity rows to name their target via a light org-to-org link — not built now.
- **ProjectContact** — the single person-grain join: one row per (`project_id`, `contact_id`, `role`), covering *everyone* involved — internal RMI staff, contractor personnel, and client/party contacts alike. A contact holds multiple roles via multiple rows (the client's primary contact who is also the billing contact: two rows). "Who do we call at organization X" is a query, not a column — the contact's organization is already on the Contact record, so there is no separate per-org-role PoC field to keep in sync. Directory data only — never access control.

**Contacts vs. users: linked, never merged.** A Contact answers *who a person is* (directory); a `platform.user` answers *who can authenticate* (a principal with grants). The populations overlap but neither contains the other: internal RMI staff are Contacts under the RMI Organization (RMI itself is just an Organization in the registry — no special-casing) and are already Users via Portal SSO; contractors may or may not hold Portal accounts; client contacts are typically never Users until #261. The nullable one-to-one link (`contact.user_id`, unique where present) is wired in v1 so the workspace can show "has platform access." *How* a linked user authenticates — Portal SSO today, the #261 restricted login later — is recorded on the identity side and never leaks into the Contact schema; that is exactly what lets #261 land as "create a user on a second auth backend, link it to the existing Contact" with zero registry migration. Two invariants: **being a Contact never grants access** (grants remain explicit per (user, project, module); the link is informational), and deactivating either side never cascades into the other.

Mutations go through a platform service and ride the caller's transaction into audit (`DbAuditSink`), like every other platform-owned write.

**Migration from the #123 strings**: backfill Organizations from the distinct `client_name` / (`railroad_name`, `railroad_mark`) values with a deliberate dedup pass ("same railroad spelled three ways" is resolved by a human, keyed on the AAR mark where present). The string columns then become **denormalized display snapshots with the registry service as their single writer** — the admin project form's client/railroad fields hand off to the registry at the same migration, so nothing else writes them — and existing consumers (project home, exhibit headers) keep reading them unchanged. The cleanup wave verifies snapshot-vs-registry agreement before dropping the columns.

### The `pm` module

A real module — `modules/pm/`, schema `pm`, `require_module_access("pm")`, own Alembic chain — following the SBIS anatomy. Module-not-platform-web is deliberate: when #261 clients reach the project home, internal PM material sits behind a grant clients are simply never given. The module owns:

- **The workspace UX**: the project-scoped pages where a PM maintains parties, lifecycle, scope, and documents without `/admin`.
- **Property scope** (`pm.property`): structured, not prose — `property_type` (`railroad` \| `other`), asset categories under valuation as a multi-select (`land`, `track_improvements`, `building_improvements` — one or a mix), and subdivisions as a repeatable list. Modeled as its own light entity with a project FK from day one so multiple properties can roll up later; v1 UI assumes one property per project and keeps the fields thin. Module-side placement was pressure-tested against the modules as-built: TIVS carries `rr_subd` as a nullable string attribute copied from GIS onto inventory rows, CIV keys direction-label settings by subdivision string, SBIS filters by `sub` — **no module models a subdivision entity**; all consume GIS attribute strings. `pm.property`'s list is scope metadata, not a competing model; if a shared subdivision entity ever emerges (subdivision names recur on deliverables and may deserve the reference-data treatment roles got), that is the promotion trigger.
- **Fee planning** — the **planning/estimate side only**. No actuals, no invoices, no WIP, no time: those are QBO's. This boundary also keeps realized-fee and margin data structurally absent from anything #261 could ever surface, and it is unchanged.

  *Amended by #1254 (2026-08-21).* What this ADR shipped was a placeholder: `pm.fee_estimate` (a low/high range) plus free-typed `pm.fee_rate` lines. That is superseded by the fee-estimate model specified in `docs/planning/pm/fee-estimate/SPEC.md` — twenty-one tables covering an effective-dated task catalog and rule engine, per-resource travel and expenses, versioning, and a snapshot frozen at issue. The two placeholder tables are dropped in the same revision that creates the new model.

  Two boundaries the replacement makes sharper rather than looser. **Identity stays the project's**: the estimate stores no copy of code, name, client, railroad or location, resolving them through platform services, and its one identity column is a `client_contact_id` reference into `platform_core.parties`. **Consultants are organizations**, not names typed into an expense row. Both follow this ADR's own registry-is-the-single-writer rule; a fee estimate carrying its own copies would have been the fourth place for the same fact to be wrong.
- **The reference-document shelf** (`pm.document`): a curated index, explicitly *not* a SharePoint replacement. An entry is **either an uploaded file** (existing storage backend, `scoped_key`, access-checked streaming — the SBIS as-built-plan pattern) **or a link out** (SharePoint or elsewhere). Categories: `client_provided` (maps/surveys), `proposal` (signed), `correspondence` (key threads). Uploads and deletions are audited. Entries — external links included — are internal-by-default under the sensitivity rule, and a projected link is never a grant bypass: the target's own permissions (SharePoint's) still gate access to the destination.

### Lifecycle (platform-core)

`platform.project.status` today is exactly `active` \| `archived`, and it gates the picker and admin list — that is an *operational visibility switch*, not a lifecycle. Rather than overload it, the project gains a separate nullable **`lifecycle_stage`**: `proposal` → `awarded` → `fieldwork` → `analysis` → `review` → `delivered` → `closed`, plus key dates (`awarded_on`, `target_delivery_on`, `delivered_on`, `valuation_date`). Backfill does not guess: existing projects start with a null stage and PMs fill them in. `status` stays orthogonal (a `delivered` project is archived eventually). Stage and dates live platform-side because they are display-grade, non-sensitive, and the project home renders them. `valuation_date` is the **canonical project-level appraisal effective date**: any module needing an as-of date reads it (TIVS's per-entry `effective_date` is cost-vintage metadata on cost-book rows, not a competing valuation date — the two never contradict because they answer different questions). One consequence accepted for v1: a prospect (status `active`, stage `proposal`) appears in the project picker; with three users that is tolerable, and a lifecycle filter on the picker is a later nicety, not a blocker.

### Cross-cutting rules

- **Field-level sensitivity from day one.** Every field added under this ADR is tagged client-visible vs. internal at the point it is added — Wave 1's registry and lifecycle fields included; the default is internal. The tags live as a declared allowlist in code (per table), which the #261 wave consumes as its projection — nothing is "filtered out later," and projections are allowlist-driven: an unknown or untagged field is denied by construction, so a future column cannot become client-visible by merely appearing in a query or serializer. Fee internals, contractor terms, and internal notes are internal categorically.
- **Minimal required fields.** A project — past (backfilled) or future (prospective) — is creatable with code + name + status alone; everything added under this ADR is optional, **including the client link**. A proposal-stage stub is exactly the moment one may not want to create-and-dedup an Organization yet; the client link is *expected* by `awarded` (surfaced as a workspace nudge, never a database constraint). Historical import and pipeline stubs must not stall on paperwork.
- **Seams designed now, kept shallow** (no speculative build-out): the document attach-target admits an organization-scoped document later (master agreement) without a schema break — an entry attaches to exactly one of project/organization, enforced as a database XOR check rather than a caller convention, with only project wired in v1 (enabling org scope later is additive: a nullable column and a widened check, existing rows untouched); billing rates admit a shared rate-card reference later (free-typed in v1); a QBO reference (customer id on Organization, job id project-side) deliberately ships **no placeholder columns** — nullable id columns are a trivial additive migration if a read-only glance is ever built, and the ownership boundary above is the durable part of the decision; the workspace admits per-module engagement summaries (TIVS/CIV/SBIS chips) via a light provider contract each module adopts on its own timeline.

## Explicitly out of scope — by design, not by deferral

- **Time tracking and invoicing** — owned by QBO permanently. Nothing QBO-shaped ships now, not even placeholder columns; a future read-only reference (customer/job ids) would be a trivial additive migration and the only thing that ever crosses that line.
- **Full document management** (versioning, approvals, retention) — SharePoint's job.
- **Project financials**: margins, actuals-vs-estimate profitability.
- **Task/checklist/deliverable tracking and scheduling.**
- **Prospecting/CRM pipeline** — the `proposal` stage is the hook; the CRM is not built.
- **Cross-project reporting/analytics dashboards.**
- **The client portal itself (#261)** — the data model anticipates it; the portal is its own later wave with its own ADR.

## Open questions (review log)

**Review 2026-07-17 (all resolved)**: questions 1–7 confirmed as recommended. Question 8 resolved by deferral — no QBO columns ship at all, not even placeholders (adding nullable ids later is a trivial additive migration; the ownership boundary is the durable decision). Question 9 was superseded in review — a fixed staffing vocabulary was the wrong frame (RMI is three people, effectively all appraisers; the real need is roles for *external* contacts that are often known informally before they fit a vocabulary) — and became the PartyRole reference-data design in the Decision, which also absorbed the per-org-role PoC column into ProjectContact. Question 10 resolved: no auto-backfill — at three employees, hand-entry is faster than a migration. Question 11 (the seeded well-known role sets) confirmed as proposed.

1. **No organization-type enum** — recommended. A railroad is an Organization with a `reporting_mark`; everything else is a role on a project. Adding a `kind` column bakes in exactly the rigidity the role join avoids. Confirm, or name the org-level distinctions that matter.
2. **Railroad dedup on the AAR mark** — recommended: partial unique index on `reporting_mark` where present; the backfill dedup keys on it. Marks are stable and short; name spellings are not.
3. **One primary client per project** — recommended: partial unique index (`project_id`, `is_primary=true`, role `client`). Multi-client billing splits, if they ever occur, become additional non-primary client rows.
4. **Contact name shape** — recommended: single `name` display string + `title`, not given/family splits. Nothing on the platform sorts by surname; deliverables print display names.
5. **Property scope lives module-side, not on `platform.project`** — a deliberate deviation from reading #262 literally ("project record carrying structured scope"). Rationale: no second consumer exists yet (rule of three), and the module fence keeps scope details off the #261 surface until deliberately exposed. Promote to platform-core when a second consumer (e.g. TIVS) materializes.
6. **Module key `pm`** — chosen over `proj` (collides conceptually with platform-core `projects`) and `pmo`. Schema `pm`, version table `alembic_version_pm`, routes under `/pm`.
7. **Project-level valuation date** — flagged addition, not in #262: appraisal projects have an effective valuation date, and nothing owns it today (TIVS `effective_date` is per cost-book entry). Recommended: add `valuation_date` to the platform key-dates set alongside the lifecycle dates. Confirm or strike.
8. *Resolved by deferral — no QBO columns now (see review log). If a read-only glance is ever built: customer id belongs on Organization, job id project-side (QBO jobs are sub-customers mapping to projects).*
9. *Superseded in review — see the PartyRole design in the Decision (roles are in-app-extendable reference data with protected well-known keys; ProjectContact absorbed the per-org-role PoC).*
10. *Resolved in review — no user→Contact auto-backfill; RMI's three employees are hand-entered. The `contact.user_id` link itself stays in Wave 1.*
11. **Seeded well-known role sets** — confirmed, then amended across the review rounds to the final set: organization `client`, `railroad`, `property_owner`, `equity_owner`, `contractor` (the initially seeded bare `owner` was replaced by two referent-explicit roles — see round-two log); contact `primary`, `billing`, `appraiser`, `project_manager`. These are the keys code may reference (letterhead reads the primary `client`, exhibit headers read `railroad`, allocation reads `role_key = 'equity_owner'` for `ownership_pct` rows) and the app protects — everything else is added in-app as needed.

**Second review round 2026-07-17 (external review, post-acceptance)** — six findings plus one owner-requested addition, all resolved by amendment in place:

1. `owner`/`property_owner` redundancy — confirmed, then sharpened on a further pass: the bare `owner` was hiding **two different relationships**, not one concept with a naming wart. Resolved as two roles with self-evident referents — `property_owner` (owns the appraised property) and `equity_owner` (stake in the property-owning entity) — plus nullable project-scoped `ownership_pct` on equity rows (owner decision: RMI allocates appraised value by stake; point-in-time by design so JV re-caps never restate history). A brief intermediate collapse to a single `property_owner` was itself superseded.
2. Dedup over time — confirmed gap, the strongest finding: added `organization.is_active`, an audited merge/redirect operation (Wave 1a service), and search-existing-first as the Wave 2 picker contract.
3. Primary-client constraint hole + key stability — fixed: the partial unique index predicate names both conditions (`role_key = 'client' AND is_primary`), and join rows store the stable string `role_key`, never a seeded surrogate id.
4. Property-scope placement — pressure-tested and upheld with facts recorded: no module models a subdivision entity (TIVS `rr_subd`, CIV settings keys, SBIS filters are all GIS attribute strings); a shared subdivision entity is the named promotion trigger.
5. `valuation_date` authority — defined: project-level canonical appraisal effective date; TIVS per-entry `effective_date` is cost-vintage metadata, not a competitor.
6. Client link at creation — loosened to optional (expected by `awarded`, workspace nudge, never a DB constraint); proposal-stage picker clutter accepted for v1 (three users), lifecycle filter noted as a later nicety. Minor notes acknowledged without change: single-valued contact `email`/`phone` is a deliberate assumption; the `property_type`/asset-category combination guard is Wave 2 form UX.
7. Added during this round (owner request): **addresses** — structured-lite on Organization and Contact, with contacts assuming the organization address by resolution rule unless overridden; billing-vs-physical split is the promotion trigger for an address entity.

## Consequences

- Exhibit letterhead (#134), deliverable addressing, and #261 logins gain a durable party model instead of parsing strings; the dedup debt in `client_name`/`railroad_name` is paid once, at backfill, with humans in the loop.
- The contact/user split is settled ahead of #261: the portal wave creates principals and links them to existing Contacts; auth mechanics (Portal vs. restricted) stay on the identity side, and no registry migration rides that wave.
- The platform gains a fourth module whose fence is load-bearing for security, not just organization — the pattern (module = grant boundary) is reaffirmed ahead of #261.
- `status` semantics stay stable for the picker/admin; lifecycle arrives as new, nullable, honest data rather than a forced reinterpretation of `active`.
- The QBO and SharePoint boundaries are recorded as *permanent* ownership decisions with a standing test, so future "just add invoicing" requests have a documented answer.
- The registry service maintains the denormalized strings during the transition window — dual-write cost accepted so the cutover never breaks project home or shipped exhibits; the cleanup wave removes it.
- Scope restraint is explicit: v1 delivers a client/document/lifecycle layer other modules read from, not a general-purpose PM tool.
