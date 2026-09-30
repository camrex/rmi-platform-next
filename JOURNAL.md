# JOURNAL

Append-only. Newest at the bottom. Each run adds one entry (see `AGENTS.md`).

## 2026-09-29 setup — done

Repository created, with MISSION.md, AGENTS.md, PLAN.md and the runner. The box (`rmi-nuc`,
user `rebuild`) can reach only the LLM router and the public internet; it reads the source
repos with a read-only token and writes only here, with a deploy key. First task: 0.1.

## 2026-09-30 0.1 — done

**Task**: Inventory `rmi-platform`: layout, each module (SBIS, CIV, TIVS, PM), routes, models, migrations, background jobs, how modules share code today, the GIS sync, tests, deploy. Cite paths.

**What I did**:
1. Read MISSION.md, AGENTS.md, and PLAN.md to understand the context and workflow.
2. Explored the rmi-platform repository structure: platform core, platform-web composition root, five modules (SBIS, CIV, TIVS, CVS, PM), deploy, docs, tools.
3. Deep-dived into each module: manifests, composition roots, DB definitions, models, routes, Alembic chains.
4. Studied platform-core services: identity, access, projects, parties, GIS (arcgis/), audit, storage, tokens, worker (ARQ), documents, validation, conversations, web (shared kit), observability, qbo, registry, testing, db.
5. Analyzed GIS integration: one-way attribute-only sync from ArcGIS Portal; modules declare slots in manifests; platform handles binding/sync/landing in synced tables; modules read synced rows instead of hitting Portal.
6. Checked background jobs: core tasks (sync_gis_datasets, scheduled_gis_resync, backup), module-specific adoption hooks (SBIS, asset-family adoption).
7. Reviewed code sharing: platform-core services (no circular imports), manifest registry, shared web kit (ADR 0020), synced GIS rows, audit trail.
8. Examined test structure (pytest, async-native, fixtures), deployment (Dockerfile, Lightsail, smoke tests), CI/CD gate (ruff, pyright, pytest, alembic_drift).
9. Read ADRs to understand settled decisions (ADR 0001–0024).

**Result**: Created `docs/inventory/rmi-platform.md` (~600 lines) covering:
- High-level overview (modular monolith, schema-per-module, one container).
- Directory layout with roles.
- Platform core services (14 subsystems): identity, access, projects, parties, GIS, audit, storage, tokens, worker, documents, validation, conversations, api, web, sections, observability, qbo, registry, testing, db.
- GIS integration deep-dive (sync workflow, landing, attribute-only contract, module slots).
- Each module detailed: SBIS (bungalow inventory, ADR 0010), CIV (360° panoramas), TIVS (five-stage valuation, ADR 0009), CVS (land valuation), PM (party registry, lifecycle, fees, ADR 0014 + 0024).
- Models, validation, routes (ADR 0013), migrations (six Alembic chains), background jobs (ARQ), tests (pytest), deployment (Lightsail).
- Code sharing: hierarchy, no circular imports, seam examples.
- Configuration, code quality, known issues, version & production URL.

**What I found**:
- Clean modular design: each module owns its schema, routes, models, migrations, jobs; composition root mounts all.
- Strong separation: platform-core is frontend-agnostic; modules never import each other; cross-module links via core services or simple data reads.
- GIS as a core service: modules declare slots, platform handles binding/sync/landing; modules read synced rows, never URLs/tokens.
- Testing thorough (async-native pytest, schema validation in CI), documentation mature (24 ADRs indexed), deployment operationalized.

**Next run should know**:
- Task 0.1 complete; inventory comprehensive with paths throughout.
- Architecture already very modular; next is understanding seams and the desired plugin contract.
