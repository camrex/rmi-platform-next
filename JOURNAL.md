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

## 2026-09-30 0.2 — done

**Task**: Inventory `rmi-sbis-extract`: what the extraction pipeline does end to end, the part catalog's structure, what it produces, what SBIS could consume from it.

**What I did**:
1. Read MISSION.md, AGENTS.md, PLAN.md, and JOURNAL.md to understand the context.
2. Deep-dived into rmi-sbis-extract: explored M0–M12 working documents, examined code structure (12 directories in src/sbis_extract, 5 major stage pipelines), read HANDOFF.md (proof-of-method Kedzie run) and CATALOG_ENTRY_SPEC.md (comprehensive reference, 1,174 lines).
3. Traced the full pipeline: M0 (ingest, sheet classification) → M1 (deterministic vector parsing: 1,097 contact references) → M2 (vision pass for rasters) → M3 (identification: coil + relay class + features → part number) → M4–M8 (verification and inventory proposal) → M9–M12 (audit and field work).
4. Studied the catalog redesign: current SBIS has 503 rows with compound identifier columns, no issuer tracking, no confidence recorded, discriminating attributes in prose. Proposed shape: one JSON per part, with typed identifiers (value, issuer, kind, era, source), attributes (coil, arrangement, polarity, duty), classification (path), relations (plugs-into, equivalent-to, is-part-of), per-claim sources/confidence.
5. Measured what exists: 569 identifier rows transcribed (Alstom P1457, UP material reference, Siemens cross-reference); 27 SBIS rows resolved to manufacturer P/N; 676 relays at Kedzie identified to 6 confidence tiers; 6 of 25 Bungalow A rows appear on drawings, 19 do not.
6. Identified data contract: SBIS is source of record (ADR 0010), project produces proposals, never writes back. Instances need source/confidence fields; identifiers table replaces compound strings; uniqueness on (bungalow, catalog_item) must be dropped.

**Result**: Created `docs/inventory/rmi-sbis-extract.md` (~830 lines) covering:
- Pipeline architecture (M0–M12 stages with code paths and file references).
- Models (Drawing, Evidence, ContactRef, PositionScheme, Provenance, Reading).
- Parsers (relay_layout, rack_layout, circuit_vector, power_dist, tower_indication).
- Identification logic (coil + class + features → part number, 6 confidence tiers).
- Catalog structure (identifiers, attributes, classification, relations, traceability; why current SBIS fails; proposed JSON shape; data day one).
- Outputs (manifest, contact references, audit trail tabs, loader, instance proposals, reconciliation workbook).
- What SBIS can consume (relay counts, non-relay proposals, P/N corrections, catalog replacement, new queries).
- Known limitations (raster sheets, front/back accuracy, stub counting, thin identifications, assembly granularity, GIS mapping).
- Reference documents (permanent vs. working).
- CLI surface and test coverage.

**What I found**:
- Pipeline is mature and well-documented: proof-of-method (535 Type B, 129 Type J, 16 timers at Kedzie) through M0–M8 with documented findings per stage.
- Catalog redesign is thorough, grounded in evidence (283 rows cited in CATALOG_ENTRY_SPEC.md). Addresses real defects in current SBIS.
- Data contract clear: SBIS authoritative, project proposer; GIS runs downhill (TIVS reads SBIS, not reverse, per ADR 0010).
- Coverage gaps measured: 7 of 53 queue bungalows on fully scanned sets (111 of 688 est. rows); 151 of 364 Lake St Tower relays thin; Chandrayaan-like sets without text layers limit text extraction.
- Next work: UP Asset Audit integration (M11, M12, independent source Sept 2026); field sessions (Lake St, nameplate reads); second railroad's material reference.

**Next run should know**:
- Task 0.2 complete; rmi-sbis-extract fully inventoried with paths.
- Catalog redesign is critical path: separates identifiers from names, adds traceability, JSON-per-part. 569 identifier rows contributed day one; 27 SBIS rows resolvable now.
- SBIS integration architecturally clear (proposals not writes; identifiers table; instance evidence fields; dropped uniqueness).
- Pipeline has known technical limits (raster, vision accuracy, stub counting) and open design questions (assembly granularity, GIS mapping, second railroad).
