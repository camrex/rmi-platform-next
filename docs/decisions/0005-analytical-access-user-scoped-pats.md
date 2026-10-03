---
status: ruled
kind: architecture
date: 2026-06-03
refs: []
source_status: "Accepted (2026-06-03)"
imported_from: rmi-platform/docs/adr/0005-analytical-access-user-scoped-pats.md
imported_on: 2026-10-03
---
# 0005 — Analytical access: user-scoped personal access tokens

**Status**: Accepted (2026-06-03)

## Context

Analytical clients (Excel Power Query, Power BI, ad hoc reporting) cannot use the interactive ArcGIS SSO flow ([core spec §4.5](../planning/IDEAL_CORE_STACK_SPEC.md)). TIVS/CVS today expose access via **shared, admin-issued, project-scoped, SHA-256-hashed read-only API keys** (`X-Project-API-Key`). The spec's target evolution is **user-scoped, self-service PATs bounded by the user's live permissions**. Decision: build the target model now rather than shipping the shared-key mechanism and migrating later.

## Decision

Build **user-scoped personal access tokens** as the MVP analytical-access path:

- A PAT **identifies a user**; its authorization is **derived from the user's effective project/module access, resolved live at request time** — never a permission snapshot baked into the token. Revoking the user's access or deactivating the user immediately constrains/invalidates the token.
- A PAT **can never exceed** the issuing user's grants, but the user may **narrow** it (single project, e.g. `read:inventory` only, shorter TTL).
- Each PAT is individually named, attributable, **revocable**, **expiring**, and **audited** (issue / use / revoke), with last-used tracking.
- Storage reuses the proven mechanism: **hashed token** at rest (never stored plaintext), read-only scopes, presented over a stable, versioned, paginated HTTP surface consumable via Power Query `Web.Contents`.
- Carry forward the hashing/scope/expiry/last-used patterns from `rmi-tivs` `project_api_keys.py`; the change is the trust boundary (per-user least-privilege), not the consumption pattern.

### Resolved specifics (spec §4.5 open questions)

- **Who may mint**: any authenticated user who holds at least one project/module grant may self-issue a PAT from their profile. This is safe because a PAT can never exceed the issuer's live access.
- **Span**: a single PAT **may** cover multiple projects/modules, but only within the user's effective grants; the user may narrow it. Authorization is always recomputed live, so a broad PAT automatically shrinks as the user's grants shrink.

### Deferred

- An optional **least-privilege read-only PostgreSQL role** for direct ODBC/Power Query access (spec §4.5) is deferred; revisit if API-shaped access proves insufficient.
- A Power BI custom OAuth2 connector is deferred; PATs cover the immediate Excel/Power Query need.

## Consequences

- No future migration from shared project keys to user PATs — the trust boundary is correct from the start.
- Requires live authorization resolution on every analytical request (token → user → current grants), reusing the same project/module authorization as interactive access. Slightly more per-request work than a static key check; acceptable and more secure.
- Audit and revocation are first-class from day one.
