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

## 2026-10-01 0.3 — done

**Task**: Inventory `rmigis-agp-toolbox`: the YAML schema definitions, every feature class and field, topology rules, Survey123 forms, how the toolbox applies them.

**What I did**:
1. Read MISSION.md, AGENTS.md, PLAN.md, and last JOURNAL entries to contextualize.
2. Explored rmigis-agp-toolbox repository structure: one ArcGIS Pro Python Toolbox entry point, 23 tools, 27 shared utilities, 3-domain YAML schema bundles (track improvement, real property, building & site).
3. Studied YAML schema organization: directory-based per-domain with `_shared.yaml` metadata + individual feature class YAML files. 35 FCs total across three domains.
4. Analyzed Track Improvement schemas: 21 feature classes (points, lines, polygons, tables) for railroad corridor inventory. Field catalog with 400+ fields, template inheritance, 27 coded-value and range domains. Topology design (suspended, rank-based, per-FC YAML metadata).
5. Examined Real Property and Building & Site schemas: 11 + 3 FCs respectively, with field inheritance patterns and domain controls.
6. Traced schema loading (`utils/schema_yaml.py`): directory or single-file source, field template resolution with inheritance chains, type canonicalization, validation output.
7. Studied FC creation orchestration (`utils/fc_orchestrator.py`): 4-stage pipeline (load schema, prepare domains, plan actions, create FGDB, copy to EGDB, cleanup).
8. Reviewed domain sync (`utils/domains_io.py`): safe additive-by-default sync with dry-run, never removes codes without explicit flag.
9. Examined service auditing and in-place field updates (`utils/service_audit.py`, `tools/apply_schema_fields_tool.py`): read-only portal comparison, field additions/removals with backup.
10. Checked for Survey123: none found in rmigis-agp-toolbox; MISSION.md notes Survey123 is in rmi-platform CIV module for OID virtual inspection.
11. Read EGDB_UPDATE_WORKFLOW.md (phase guidance, recent breaking changes in xing_inv_pt), TRACK_IMPR_TOPOLOGY_IMPLEMENTATION_PLAN.md (suspended but complete design), YAML_TOOLBOX_MIGRATION_PLAN.md (arcgispro-yaml-pyt modernization).

**Result**: Created `docs/inventory/gis-schemas.md` (~800 lines) covering:
- Overview: YAML-driven ArcGIS Pro toolbox, 35 FCs across three domains, 400+ field definitions, 27 domain definitions.
- Schema structure: directory-based per-domain with `_shared.yaml` + per-FC YAML. Track Improvement (21 FCs, 400+ fields, 27 domains), Real Property (11 FCs, 120+ fields), Building & Site (3 FCs, 50+ fields each).
- Field definitions: inheritance from templates (id_base, yes_no_base, mp_base, year_base, etc.), per-FC field catalogs, relationship fields, inspection fields, flexible attributes, editor tracking.
- Domain definitions: 27 coded-value and range domains across track types, weights, frog sizes, inspection ratings, detector types, tank sizes, generators, etc.
- Topology design: per-FC YAML metadata (include, rank, rules), rank-based (1=authoritative, 4=refinement), baseline rules (Must Not Self-Overlap, Must Be Covered By, Must Not Have Dangles), suspended pending ArcGIS compatibility.
- Survey123: none in toolbox; lives in rmi-platform CIV module for OID virtual inspection.
- How applied: schema loading (directory or single-file, inheritance resolution, validation), FC creation orchestration (4-stage pipeline FGDB→EGDB), domain sync (additive, dry-run capable), service auditing (case-insensitive field comparison, severity grading), in-place field updates (backup, service stop/restart, domain values sync).
- Configuration: `config/settings.yaml` paths, defaults, schema locations, Portal/server URLs.
- Known issues: xing_inv_pt (13 fields removed, data loss risk), recent field additions and renames, domain changes (new rail_grade, pnt_type; modified bglw_use, bglw_size, xing_config).
- Future work: migrate to arcgispro-yaml-pyt framework for better testability and dev ergonomics.
- File paths: all tools, utilities, templates, domains, field catalogs, layer files, reference data, maintenance scripts, documentation.

**What I found**:
- YAML schemas are mature and well-structured: directory organization allows per-FC updates without whole-file manipulation; template inheritance reduces duplication; domains are explicitly defined and validated.
- Toolbox is operationally sound: safe defaults (additive, dry-run capable), comprehensive logging, multi-stage pipeline with rollback-friendly backups, service integration tested.
- Topology framework is complete but disabled: design is sound (per-FC YAML metadata, rank-based authority, baseline rules defined), implementation code preserved, just waiting for ArcGIS Pro compatibility fix.
- No Survey123 in toolbox: consistent with MISSION.md; CIV module owns it for OID virtual inspection.
- Recent maintenance activity (xing_inv_pt restructure, new domains, field renames) shows schemas are actively evolving; breaking changes are documented and phased via EGDB_UPDATE_WORKFLOW.md.
- Modernization planned but blocked: arcgispro-yaml-pyt framework design complete, but migration is future work.

**Next run should know**:
- Task 0.3 complete; gis-schemas.md comprehensive with file paths, field/domain counts, topology design, tool workflows.
- Schema design is sound and operationally mature; no blockers for MISSION's "better GIS schemas" objective beyond what's already in the pipeline (topology re-enablement, potential arcgispro-yaml-pyt migration).
- Ready for task 0.4 (rmigis-pyt and rmi-imagery-tiling inventory) and 0.5 (GIS schema review / optimization analysis).
- Survey123 is a red herring for this inventory; belongs in platform, not toolbox.

## 2026-10-01 0.4 — done

**Task**: Inventory `rmigis-pyt` and `rmi-imagery-tiling`: what each does and what the platform uses or could use.

**What I did**:
1. Read MISSION.md, AGENTS.md, PLAN.md, and JOURNAL.md to contextualize.
2. Explored rmigis-pyt: README, CLAUDE.md (architecture guide), source structure (core, adapters, tools, registry). Read 24 tool implementations, ~5KB pure core logic, ~2KB adapter layer. Studied purity enforcement (ruff TID251 bans arcpy/arcgis in core), settings (Pydantic + YAML), manifest-driven setup, partial-success tracking.
3. Explored rmi-imagery-tiling: README, CLAUDE.md (status, decisions), SPEC.md (5-phase build), RUNBOOK.md (deploy, backfill, validate). Read tiling core (keys.py, tiler.py, events.py), Lambda wrapper (handler.py), Terraform IaC, backfill/validation scripts. Traced deployment (ECR, Lambda 3008MB/120s, reserved concurrency 200, S3 buckets, event trigger).
4. Examined tile-contract.v1.json: authoritative single source between tiling pipeline and CIV; per-frame: base.jpg (2048x1024 q80) + 128 tiles (768x768 q80, 16x8 grid), 129 objects total, immutable cache headers.
5. Traced platform integration: CIV module reads tile-contract.v1 in pano.py (tile_root() derives frame root from OID imagepath), settings.py (image_resolver strategy, tiles_base_url, frame_source).
6. Analyzed production status: rmigis-pyt in per-tool migration (3 of 24 live); rmi-imagery-tiling fully deployed 2026-07-02, all three projects backfilled (113K + 51K frames), event trigger live, zero failed tasks.
7. Identified integration seams: rmigis-pyt outputs -> Portal feature services -> platform GIS sync -> modules read synced data; rmi-imagery-tiling outputs -> S3 tiles -> platform HTTP GETs + browser.
8. Documented future use cases (schema validation lib, field/domain sync patterns, async task patterns, contract-driven design).

**Result**: Created `docs/inventory/gis-tools-and-tiling.md` (~1,250 lines) covering:
- Overview (two independent tools, read-only platform integration, async).
- rmigis-pyt (14 sections): architecture (purity separation, registry, config), ~24 tools across 6 categories (project setup, FC creation, field sync, data mgmt, publishing, real property, admin, map), code structure, key patterns (manifest-driven, dry-run as default, partial-success), platform integration (Portal feature services -> GIS sync), dev/deploy (Windows ArcGIS Pro, pytest headless + contract suite, three-role environments), known limitations.
- rmi-imagery-tiling (12 sections): purpose (equirectangular -> tiles), architecture (pure core + boto3 wrapper), tile contract (JSON, 129 objects/frame, immutable), components (tiling core, Lambda wrapper, recursion guard, Terraform, backfill/ops scripts), code structure, key patterns (idempotency, whole-frame failures, separate derived bucket, lifecycle), production status (backfilled 164K frames, event-driven), platform integration (CIV consumes tiles, tile URLs, settings), development (local tests no AWS).
- Seams with platform (GIS sync, imagery streaming, failure modes).
- Known limitations & future work (both repos).
- Key file paths for both.

**What I found**:
- rmigis-pyt is well-architected rewrite: pure/adapter separation enforced by tooling, settings in pydantic, manifest-driven (closes convention gaps in old toolbox), dry-run as default-safe, partial-success reporting. ~24 tools live; 3 in migration; others await office smoke tests. Three-role environment distinction (Pro runtime, GIS dev, non-GIS CI) has bitten before; dev box is richer than CI.
- rmi-imagery-tiling is proven at scale: tiled 164K frames (all three projects), zero failures, ~7 s/frame post-optimization. Contract is JSON on disk (tile-contract.v1.json); Lambda + S3 fully independent of platform. Idempotency via HEAD short-circuit; force flag via env + Batch userArguments; recursion structurally impossible + code guard. Event trigger live on originals.
- Both tools are general-purpose and extraction-worthy: rmigis-pyt's schema validation + field sync logic is reusable; rmi-imagery-tiling's tiler is pure and deployable elsewhere; both exhibit contract-driven design patterns.
- Platform never drives these tools; only consumes outputs. Seams are read-only (feature services, S3 tiles). Decoupling is clean.

**Next run should know**:
- Task 0.4 complete; inventory comprehensive with architecture, code paths, production status, integration seams, future use cases.
- rmigis-pyt ~24 tools live with ~3 in migration; no blocking issues, awaiting office validation.
- rmi-imagery-tiling fully deployed, proven at 164K frames, live event trigger, nearly zero ops cost ongoing.
- Both repos have extraction value (schema lib, async patterns, contract design) for future platform features.
- Ready for task 0.5 (GIS schema review / optimization) and 0.6 (seams analysis across all discovered repos).

## 2026-09-30 0.4b — done
Wrote `docs/inventory/rmi-platform-issues.md` (unbuilt features by module, decisions settled in
threads but not in ADRs, recurring bugs/weak seams, 14 rebuild implications, open owner questions).

**How thorough**: read the problem/decision parts of every open issue (heads and owner comments,
not every measurement table); #1236 (405 KB rolling handoff) only skimmed; ~40 closed issues opened
from index titles. Cross-checked against ADR text by grep and `docs/planning/OWNER_RULINGS.md`.

**Found**: most thread decisions live in OWNER_RULINGS.md (a second decision store). Biggest weak
seams: three identity keys (GlobalID/OBJECTID/Asset ID); "absent vs undecided vs excluded vs failed"
collapsed into silence; SBIS→TIVS seam loses price provenance; numbered slot columns; Python-string
CSS/JS/URLs; CI asyncpg loop flake (root cause never found — first diagnosis was wrong).
Tabled by the owner, so do not design around them: documents (#1298/#601/#1299), valuation year (#950).

**Next run should know**: the write-back design (#866 slices) and the GIS schema asks (#1042, #1026,
#896, #746, #747, #729) feed task 0.5; the seam findings feed 0.6 and the architecture proposal.

## 2026-09-30 02:46 UTC 0.5 — runner

Runner: ended without finishing (exit 1), attempt 1 of 3.

```
Connection error.
```

## 2026-09-30 0.5 — done
Wrote `docs/inventory/gis-schema-review.md`: ten ranked proposals, each tagged P (platform/sync side),
T (template repo) or O (optional ask to the schema owner); none needs a Portal change.

**Found** (from `~/sources/rmigis-pyt/templates`, the newer repo, counted from YAML; not compared to live layers):
~13% of trk field slots are numbered-slot columns (turnout_cx 76 of 159, xing 36, wayside ontrk 26);
the same ~35 envelope fields are repeated in every FC and hand-transcribed again in TIVS `envelope.py`;
`rel_*` links (61 fields) hold asset IDs with no relationship class; yes/no, rating and year domains are
triplicated; only 3 RANGE domains exist; lat/long is bound to a rule on only 2 FCs (#1042).
The older `rmigis-agp-toolbox` has defects already fixed in pyt (YAML `OFF` boolean, `[C Confirmed]`,
`assoc_blgw_cnt` typo, unresolved-name check now raises), so the review uses pyt.
Top ranks: (1) normalise slot groups into child rows on sync, (2) declare the envelope once and take it
from the live `FieldInfo`, (3) treat stored `has_*`/`_cnt` as untrusted, (4) resolve `rel_*` to GlobalID edges.

**Next run should know**: counts of `has_*`/`_cnt`/slot fields are by name regex; Survey123 use of fields
and live-layer drift were not checked. Feeds 0.6 (seams) and the architecture proposal (per-dataset
contract: key, envelope, slot_groups, links, expectations, grammar).
