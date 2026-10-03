---
status: open
kind: architecture
date: 2026-07-25
refs: []
source_status: "Proposed (2026-07-25) · **Relates to**: ADR 0002 (tenancy), ADR 0005"
imported_from: rmi-platform/docs/adr/0017-roles-admin-tiers-capabilities.md
imported_on: 2026-10-03
---
# 0017 — Roles, admin tiers, and capabilities

**Status**: Proposed (2026-07-25) · **Relates to**: ADR 0002 (tenancy), ADR 0005
(PATs), ADR 0016 §4 (GIS write-back) · **Feeds**: #457 (capabilities), #326
(project-first grants), #327 (Admin/Settings revamp), #243 (display
templates), #261 (client logins), #437 (module modes)

## Context

The access model today is exactly two levels: a global `User.is_admin` boolean and a
`viewer|editor` role per (user, project, module) grant. That served the first year, but
it is now the bottleneck for everything queued behind it:

- **`is_admin` is overloaded.** One bit simultaneously means "may open `/admin`",
  "`can_write` anywhere I hold a grant" (`role_can_write`), and "see every project in
  the picker" — yet it does **not** confer module access (`require_module_access` still
  demands a grant row). Three semantics, one boolean, and the principal platform owner
  still has to grant themselves into every new project by hand.
- **There is no admin tier inside a project.** Module configuration surfaces (SBIS unit
  templates and catalog, TIVS cost groups, module settings pages) are gated on *editor*
  — the same role that edits inventory data. The queued features make this untenable:
  the #243 WYSIWYG display-template editor is an administration feature, not an editing
  feature, and the Settings/Admin revamp (#327) needs a tier to hang "who may configure"
  on.
- **There is no capability grain.** ADR 0016 §4 already ruled that GIS write-back must
  be a *user-explicit* permission that editor role alone must not confer — and
  deliberately deferred the permission model's shape to this ADR. `allow_viewer_writes`
  (the CIV bookmarks escape hatch) is existing evidence the role grain alone is too
  coarse.
- **PATs carry no role and scopes are enforced nowhere.** A viewer's token and an
  editor's token are indistinguishable at the API layer; `ModuleManifest.required_scopes`
  is populated by every module and read by nothing. Today this is safe only because
  every module API is GET-only — a convention, not a control.

Constraints inherited from settled decisions: authorization stays platform-owned in the
`platform` schema (ADR 0002); PAT authority is resolved live and can never exceed the
issuer's (ADR 0005); broad GIS reads are module-level posture, never a user bypass
(ADR 0016 §1); project scope stays explicit (ADR 0013).

## Decision

Three orthogonal axes, each with one job. Roles answer "how much do you steer";
capabilities answer "may you perform this specific dangerous verb". Nothing else
GRANTS authorization — PAT scopes (§5) only ever narrow what the axes already
granted, per ADR 0005's never-broadens rule.

### 1. Platform role (per user — replaces `is_admin`)

`User.platform_role ∈ {member, platform_admin, super_admin}` (default `member`).

| | member | platform_admin | super_admin |
|---|---|---|---|
| Module access | granted only | granted only | **implicit everywhere** (all projects, all modules, as project_admin) |
| `/admin` console | — | ✔ | ✔ |
| See all projects | — | ✔ (read-only listing) | ✔ |
| Grant project roles (viewer/editor/project_admin) | — | ✔ | ✔ |
| Grant platform roles | — | — | ✔ (and only here) |

- **super_admin** is the platform owner tier: automatic project_admin on every project
  and module, and the only tier that can mint or demote `platform_admin`/`super_admin`.
  The existing last-admin lockout guards move to "last active super_admin"; the
  break-glass path (`set_admin.py` → becomes `set_platform_role`) stays out-of-band.
- **platform_admin** runs the platform (users, projects, GIS bindings, tokens, audit)
  but does NOT implicitly enter module data surfaces — administering the platform and
  working appraisal data are different jobs. Their module access is granted like
  anyone's. This resolves the current admin-sees-all-but-"No access" inconsistency
  honestly: the console lists everything; the workspace requires a grant.
- Migration: `is_admin=true` → `platform_admin`; the platform owner is promoted to
  `super_admin` by break-glass. The `is_admin` column is dropped after a deprecation
  release.

### 2. Project role (per user × project, with per-module narrowing)

`viewer < editor < project_admin`, assigned **project-first** (#326): a user is given a
default role *on a project*, and module checkboxes GRANT membership at that default (a
module row may also carry a lower role than the project default — narrowing only, never
raising). *Decided at stage 3 (owner, 2026-07-25): a project role alone opens no
module — membership always comes from a module row; the grant screen's all-modules
convenience keeps the internal case one click.*

- **viewer / editor** keep today's semantics exactly (`can_write` = editor+).
- **project_admin** (new) is the in-project administration tier:
  - `can_write` everywhere an editor can, on every enabled module of that project;
  - unlocks the **admin-tier surfaces** inside modules (see §4): settings pages,
    display templates (#243), unit-template/catalog/cost-group configuration,
    readiness overrides;
  - manages that project's user grants (viewer/editor/project_admin) — delegated
    administration without platform reach;
  - does NOT touch platform wiring (GIS source bindings, module enablement, project
    creation stay platform_admin+, per ADR 0002's platform-owns-wiring posture).
- `AccessContext` gains `can_admin: bool` (true for project_admin and super_admin)
  next to `can_write` — modules gate admin surfaces with one declarative check, the
  same way they gate writes today.
- Storage: a new sibling table `UserProjectRole(user_id, project_id, role)` carries
  the project-first assignment (a magic module_key-NULL row is rejected: NULLs in the
  unique key are messy in Postgres and every existing query would need a filter);
  `UserProjectModule` keeps its exact shape, widened to the three role values and
  gaining an editor-facet narrowing list (§4 class B; empty = all facets), as the
  per-module NARROWING layer. Resolution is deterministic:
  `effective(module) = min(project_role, module_row.role if present else project_role)`
  — a module row can only lower, and no module row means the project role applies.
  The grant→auto-enable side effect becomes an explicit, labeled action in the new
  UI, and the CLI default role aligns to `viewer` (today it silently defaults to
  `editor`). *Amended 2026-07-27 (#525): even labeled, the side effect inverted the
  authority split this ADR draws — module enablement is project configuration
  (§D wiring), granting is a people decision. The grant UI now offers only the
  selected project's enabled modules, and the endpoint refuses (never enables) a
  grant on a disabled module.*

### 3. Capabilities (per user × project — the #457 axis)

Named, user-explicit permission flags for dangerous verbs, stored as their own grants
(`UserProjectCapability(user, project, capability_key)`), checked *in addition to* role:

- Capabilities are **never implied by any role — including super_admin**. ADR 0016 §4's
  reasoning (blast radius, attributability) applies to admins more, not less; the owner
  opting themselves in is one explicit, audited click.
- First capability: `gis.write_back` (ADR 0016 §4's four-axis gate supplies the other
  three axes). The vocabulary grows one explicit key at a time; no wildcard.
- Capabilities flow into PAT resolution live (ADR 0005): a token can only exercise a
  capability its owner currently holds — and only when the token's own scopes include
  it (see §5).

### 4. Feature classification rule — what each role actually touches

**Data is editor; configuration is project_admin; wiring is platform_admin.** To keep
that rule decidable without sliding into per-surface permissions, module surfaces
fall into four classes:

**A. Reads — viewer sees EVERYTHING a granted module shows.** Explicitly: a viewer on
TIVS sees inventory frames, the cost book, rates and curve assignments, RCN reports,
valuation conclusions (dollar figures), exhibits, and notes. Visibility is
**module-grain**: the way to keep someone out of costs is to not grant the module (or,
one day, the #261/#437 client tier with its own curated surfaces) — never a
role-internal read split. A per-surface read tier was considered and rejected: it is
the fine-grained trap, and there is no internal demand for it (every internal user is
an appraiser).

*Amended 2026-08-25 (#1333): "not grant the module" means not grant a KEY, and a module
may own more than one.* PM's finance surfaces sit behind `pmfee` (how a price was built)
and `pmfin` (what was billed against it) — additional keys on the same package, schema
and Alembic chain, enabled by migration wherever `pm` is. This is the sanctioned move,
not an exception to it: the alternative actually shipped first, gating those surfaces
with `admin_only=True` so that withholding revenue meant withholding project-admin
authority, and it locked out the one person whose job is the billing picture. A second
key costs a registry entry and a migration; the read tier this section rejects would
have cost a permission model. Two rules keep the escape hatch from becoming the trap:
a key is a whole surface area a person either works in or does not, and it is named in
the registry rather than derived per route.

**B. Work product & records — the editor's domain, decomposed into FACETS.** The
editor's write authority is one role but not one lump: an engagement may bring in an
outside specialist (a consulting engineer pricing costs and setting the
engineering/mobilization/contingency rates) who must not touch inventory, while an
internal appraiser edits everything. Six facets, a closed platform vocabulary:

| Facet | Owns (writes + the run triggers that mutate it) |
|---|---|
| `edit:inventory` | records & reconciliation — SBIS bungalow/equipment edits, reconcile adopt/dismiss, inventory sync triggers, CVS segment sync |
| `edit:costs` | the cost book & cost inputs, cost generation runs; CVS sales/comps entry & workbook import |
| `edit:rates` | parameter VALUES — indirect rates (engineering/mobilization/contingency, track and signal), depreciation curve/ASL assignments, obsolescence factors, scrap/substitution values; CVS adjustment factors |
| `edit:valuation` | valuation acts — RCN checks, snapshots, zero-acknowledgements, obsolescence overrides, document generation |
| `edit:gis` | the SBIS GIS-reconciliation surface — per-field apply, acks, create-from-GIS, role refresh/adopt (added Wave 13, #599: delegable without opening inventory) |
| `edit:dax` | the SBIS DAX-review surface — crossing relations and `dax_review_status` (added Wave 13, #599) |

- **A plain editor grant means ALL facets** — facets are a NARROWING list on the
  module grant row (absent/empty = full editor), the same narrow-only philosophy as
  per-module role narrowing and PAT scopes. Existing grants migrate untouched.
- The outside-engineer grant is then: editor on TIVS narrowed to
  `{edit:costs, edit:rates}` — costs and rates, no inventory, no snapshots.
- Facets deliberately stay a small closed set (four at ratification; six after
  Wave 13 added the two SBIS delegations). Splitting `edit:rates` further
  (indirect rates vs depreciation parameters) was considered and parked: if a
  real engagement demands it, that split arrives as one more facet — never
  per-field grants.
- Every module maps its write surfaces onto the vocabulary in code (the same way
  routes declare their module); a facet with no surfaces in a module is inert
  (SBIS today is effectively `edit:inventory`-only — costs/rates/valuation live
  across the ADR 0010 seam in TIVS).
- `can_write` becomes facet-aware at the write gate: the blanket unsafe-method
  check consults the surface's declared facet. Viewer semantics are unaffected —
  facets never restrict reads (class A).

**C. Configuration STRUCTURE — project_admin.** The shape things take rather than the
values they hold: module settings pages, display templates (#243), display
precision/column defaults, SBIS unit templates & catalog, TIVS cost groups and
readiness-check overrides, project user grants.

**D. Wiring — platform_admin.** GIS source bindings, module enablement, project
creation, token oversight, audit.

The value-vs-structure line in B/C is the load-bearing one: an appraiser (editor)
sets *what the contingency rate is*; a project_admin decides *which rate categories
exist and how the page presents them*. When a surface mixes both (a settings page
carrying one appraisal value), the value moves to an editor-writable surface rather
than the whole page dropping to editor.

| Tier | Summary |
|---|---|
| viewer | read every surface of a granted module; exports; own PATs and bookmarks |
| editor | class B: records, work product, parameter values, run triggers — all four facets unless the grant narrows them |
| project_admin | class C: configuration structure + project grants; implies full editor (all facets) |
| platform_admin | class D: platform wiring + administration |
| super_admin | platform-role grants; implicit project_admin everywhere |

The per-page reclassification of existing editor-gated config surfaces lands with the
Settings/Admin revamp (#327), gated on `can_admin`, using these classes — this ADR
fixes the rule so the revamp doesn't have to renegotiate it page by page.

### 5. PAT alignment

- PAT resolution carries the owner's **effective role per (project, module)** and
  capabilities, live (ADR 0005 unchanged).
- The scope vocabulary becomes real and minimal: `read`, `write`, plus capability keys.
  Enforcement: analytical GET surfaces require `read` (the current default); any future
  mutating API requires `write` AND `can_write` AND, where applicable, the capability.
  Scopes only ever NARROW (ADR 0005) — they can withhold the owner's authority from a
  token, never add to it.
- `ModuleManifest.required_scopes` is **deleted**. It is populated by every module and
  read by nothing; with the enforced vocabulary living at the API route class (GET ⇒
  `read`, mutation ⇒ `write` + capability), a second per-module declaration would only
  drift. A declared-but-unenforced permission list is worse than none.

### Explicitly out of scope (compatible extensions)

- **#261 client logins / #437 module modes**: the project-role axis accommodates a
  future `client`-tier role and per-module modes without schema upheaval; they get
  their own design pass on top of this model.
- Groups/teams, org tenancy, row-level permissions: no current demand (RMI is three
  appraisers); the axes above must not preclude them, and don't.

## Consequences

- One migration chain on `platform`: `platform_role` column (backfilled from
  `is_admin`), widened role CHECK, project-default-role storage, the editor-facet
  narrowing column (defaulting to all-facets), capability table. Deny-by-default
  onboarding at the identity boundary is unchanged.
- `require_module_access` grows the super_admin implicit path and `can_admin`
  derivation; `require_admin` becomes `require_platform_admin`. At THIS ADR's rollout
  every existing route keeps its current behavior — viewer/editor semantics change
  only via the deliberate #327 reclassification below, never as a migration side
  effect.
- Module-internal config surfaces move from editor to `can_admin` during the #327
  revamp — the one user-visible tightening (a bare editor loses settings/template
  edit access, by design).
- #243 lands admin-tier from day one: template editing gated on `can_admin`, evaluation
  visible to all roles.
- Audit vocabulary grows `access.platform_role`, `access.capability_grant` /
  `access.capability_revoke` events, in the caller's transaction as always.
