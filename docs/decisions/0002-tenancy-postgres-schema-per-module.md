---
status: ruled
kind: architecture
date: 2026-06-03
refs: []
source_status: "Accepted (2026-06-03)"
imported_from: rmi-platform/docs/adr/0002-tenancy-postgres-schema-per-module.md
imported_on: 2026-10-03
---
# 0002 — Tenancy: single PostgreSQL, schema-per-module

**Status**: Accepted (2026-06-03)

## Context

Confirms the working assumption in [core spec §3.2](../planning/IDEAL_CORE_STACK_SPEC.md). Native (in-process) modules need data isolation without the operational cost of many databases.

## Decision

- One platform **PostgreSQL** instance.
- A **`platform` schema** owns users, projects, modules, project-module enablement, user-project-module access, audit, and (later) the config registry.
- Each native module owns a **dedicated schema** (`sbis`, future `tivs`, `cvs`, …).
- **Alembic** manages migrations; the platform and each module maintain their own migration history/version table, scoped by schema.
- A dedicated **database** is reserved only for true `external_app` modules that run outside the platform process. Native modules never get their own database.
- Cross-schema references use stable project identifiers with an explicit foreign-key strategy (platform schema is the referent; modules reference platform projects, not vice versa).

## Consequences

- Strong relational integrity and transactional policy/config changes within one instance.
- Clear ownership boundary: a module's tables live in its schema; the platform never reaches into module schemas for domain data, and modules never reach into other modules' schemas.
- Migration tooling must be schema-aware (separate Alembic version tables per schema) — handled in the scaffold.
- A least-privilege read-only PostgreSQL role (for analytical/Power Query direct access, if offered) can be granted per-schema.
