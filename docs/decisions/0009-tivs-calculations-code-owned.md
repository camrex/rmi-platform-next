---
status: ruled
kind: architecture
date: 2026-07-03
refs: []
source_status: "Accepted (2026-07-03)"
imported_from: rmi-platform/docs/adr/0009-tivs-calculations-code-owned.md
imported_on: 2026-10-03
---
# 0009 — TIVS 2.0: calculation logic is code-owned; config is metadata and data

**Status**: Accepted (2026-07-03)

## Context

TIVS 1.x (`rmi-tivs`) encodes its entire calculation pipeline — field derivations, cost lookups, RCN chains, depreciation method selection — in ~26k lines of asset YAML interpreted at runtime by a 13-handler calculation engine, including per-row `exec()` of Python snippets embedded in config. The founding purpose was an **auditable path from inventory to value**; the result was an untyped bespoke DSL with runtime-only failures, no static analysis or unit testing of logic, silent config-degradation, and repeated format re-versioning (3.0 → 5.x → schema2).

Prior platform planning ([parity matrix](../planning/IDEAL_PLATFORM_PARITY_MATRIX.md), plan §7) assumed the successor would be a **versioned config-governance registry plus a constrained expression DSL** (draft→review→approved→active promotion), and made it a hard parity gate for TIVS migration.

The deep analysis behind [TIVS_2_0_PLAN.md](../planning/TIVS_2_0_PLAN.md) showed the actual change cadence lives in **parameters** (unit costs, indirect rates, curve/ASL assignments, factors) — data engineers edit routinely — not in calculation **logic**, which changes rarely and deserves code review.

## Decision

1. **Calculation logic is typed, vectorized, unit-tested Python.** Each calculator is a declared, registered object: name, plain-language methodology description, declared inputs with sources (ArcGIS field / reference table / prior stage), and version — not a bare function.
2. **Parameters are data**: project-scoped tables, edited in-app, audited in-transaction, effective-dated where the domain requires.
3. **Config is presentation metadata only** (labels, formats, tab layout): small, Pydantic-validated with `extra="forbid"`, failing at startup/CI — never silently at runtime.
4. **Auditability is preserved by construction**, not by config-readability: a **generated calculation dictionary** per asset/process (from the declarations), unit tests plus golden parity fixtures, git/PR history as the change log, and run provenance (platform version + git SHA recorded on valuation snapshots and job run-reports).
5. The config-governance registry and expression-tier DSL contemplated by the parity matrix are **not built**. Parity gate #3 is re-scoped to "versioned/audited reference data," which existing platform services substantially cover.

## Consequences

- Calculation errors become compile/test/review-time failures instead of production runtime surprises; the per-row `exec()` sandbox and its performance cliff are eliminated.
- Changing calculation logic requires a PR and deploy — accepted deliberately: that friction *is* the review control the appraisal domain wants.
- Validation falls out for free: per-record readiness/gap reports are derived from the same declared inputs (TIVS plan §4.8), so there is no second rule set to maintain.
- The ~26k lines of TIVS 1.x YAML are demoted to a **transcription spec** — the formulas are ported into calculators and verified against golden fixtures from the production system.
- If a genuine appraiser-authored-calculation need emerges post-launch, a constrained expression tier can be added *on top of* the declared-calculator registry; nothing forecloses it.
