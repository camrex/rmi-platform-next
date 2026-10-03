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

## 2026-09-30 0.6 — done
Wrote `docs/inventory/seams.md`: module↔module couplings (import counts, adapters, URL-by-shape links),
module→core calls (the de-facto contract), core/shell→module leaks, per-module offers/consumes,
planned-but-unbuilt items mapped to contract needs, and ten contract requirements (§6).

**Found** (grep over `~/sources/rmi-platform`, tests excluded): `platform_core` imports no module code;
the manifest covers about half of what a module is, the rest (routers, hooks, validation, card slots,
resolvers, tasks, cron, settings, access keys, launcher blurb) is hand-wired in about eight
`platform_web` files; four version-asserted adapters (TIVS→SBIS, and PM phase into SBIS, TIVS, CVS);
the one real leak is SBIS and TIVS importing CIV's web code (10 import lines) with no adapter; links
between modules are hard-coded URL strings in three styles (#435 asked for a registry); TIVS cannot
start without SBIS because of the seam import.
**Corrections to 0.1 inventory** (`rmi-platform.md`): TIVS does not query `sbis.models.Bungalow`, it
imports SBIS loaders only via `tivs/sbis_seam.py`; "SBIS reads PM property scope" is not in the code
(no non-test consumer of PM's `Property`).
**Not checked:** runtime behaviour, tests for link visibility, DTO fields, `tools/rmi-mcp`.
**Next run (0.7)** should know: CVS is built and mounted though MISSION does not list it, so the proposal
must decide whether it is in scope; ask about the standalone CIV viewer (#1981); the contract wants
per-feature `requires` vs `uses_if_present`, a link registry with identity kinds, and one manifest read by
both API and worker roots.

## 2026-09-30 0.7 — done
Wrote `docs/architecture/PROPOSAL.md` (~5,400 words, ~11 pages). It covers the core, the one-manifest
module contract (entry-point discovery, read by both API and worker), the add-a-module checklist and
template with a contract test, `Ref` identity kinds, a link registry with relations and stored links
(including unlink), versioned contract packages for seams with provenance, CIV cards with no host
imports, LLM conventions (MAP.md, 500-line cap, `describe` API, one decision store), GIS dataset
contracts (envelope from FieldInfo, slot child rows, rel_* edges, expectations, drift check, typed
absence), the catalog as its own foundation module (domains incl. track-side, unclassified→classify/merge,
migration from `sbis.equipment_catalog`), module mapping with unbuilt issues placed, the reference hub
as a later module, all four MISSION decisions (all stand, with evidence), 10 build phases, risks.

**Positions for the operator (§12, R-1..R-10):** rebuild as new repo with modules *ported* not rewritten
(evolve-in-place stated as viable alternative); one decision store; GlobalID-only; typed absence;
provenance on seams; slot child rows; catalog holds no prices; standalone CIV viewer deferred; CVS in
scope; ops as constraints until cutover.

**Checked in source for this run:** `sbis/models.py` EquipmentCatalog + ComponentTokenMap,
`tivs/assets/registry.py` PROCESSES, `tivs/valuation/models.py` TivsValSnapshot, `arcgis/synced.py`
GisDatasetRow, `registry/manifest.py`, fee-estimate README/SPEC, #1829, rmigis-pyt trk domains
(stand/derail/esl). Not verified: live layers, Survey123 field use, runtime seam behaviour.

**Next run should know:** the next PLAN item is behind `CHECKPOINT architecture`; wait for
`approvals/architecture.md`. After approval, turn §10 into Phase 1 tasks (phase 1 contract work = heavy).

## 2026-09-30 03:44 UTC runner — waiting

Runner: waiting at checkpoint 'architecture' (approvals/architecture.md missing).

## 2026-10-02 0.7b — done
Diff review written to `docs/inventory/changes-since-2026-09-30.md`; four inventories corrected in
place (each says "Corrected 2026-10-02"); `docs/PARITY.md` created with 10 rows.

**Found.** rmi-platform: 21 commits, `f9e4c8c..2422767`, all 2026-09-30 releases v1.60.0–v1.62.2:
RR Audit (SBIS, #1997, three new SBIS migrations, 11 tables, task `sbis_parse_rr_audit`, catalog
delete/merge `crosswalk` blocker), CVS Power Query functions, `?section=`, revision token, no-Total
`sections` view. ADR 0025 accepted (third data class: third-party evidence). SEAM_VERSION still 6;
no seam added. rmi-sbis-extract: 21 commits; fresh SBIS copy (parts 4,063 → 4,054; coverage CSV
now 505 rows: 276/49/180; the inventory's "503" and "27 of 503" were stale), power-branch naming,
bungalow-function vocabulary, chargers/cells proposal. agp-toolbox, pyt, imagery-tiling: no commits,
so the GIS inventories stand. Issues: 758 (114 open, 644 closed), new #2023, #2026, #2029;
#1981 became its own project (rmi-civ-viewer, Azure, client-hosted) which overtakes PROPOSAL R-8.

**For 0.8** (list in the changes file §4): ADR 0025 third data class; catalog blocker registry;
catalog figures for §7; CVS published-view contract and #2023/#2026; #2029 vs §9.2 (what a TIVS
snapshot freezes); R-8 rewrite; PARITY mechanism; nav declared outside the manifest.

**Where I stopped / not checked.** Done in full. Not checked: PR bodies, release-note text beyond
headers, #1236's 194 comments, production figures. Discrepancy to know: `catalog/README.md`'s SBIS
coverage table (501 rows) is behind `sbis_coverage.csv` (505); I cited the CSV. I did not edit
`PROPOSAL.md` or the three GIS inventories. The PARITY seed omits changes before 2026-09-30
(v1.59.x), which the inventories already cover. Next: 0.8 (heavy), behind the architecture
checkpoint if that is still unapproved.

## 2026-10-02 0.8 — done
Revised `docs/architecture/PROPOSAL.md` in place for the five 2026-10-02 MISSION entries and the
0.7b findings. ~6,070 words (0.7 was ~5,400); tightened unchanged prose to stay under 12 pages.

**What changed, by section.**
- §1/§2: summary rewritten; R-1 now says calculators port unchanged and only their adapters change
  (sub-modules, child rows, pricing), with per-sub-module fixtures proving numbers.
- §3.1: core gains units, a monotonic revision counter (#2023), section groups if #2026 is taken.
  §3.2 manifest example: SBIS requires pricing, RR Audit nav in the manifest, `catalog_refs`.
- §4: `pricing.price` Ref kind; money crosses as price refs, not copies; new events.
- §6.1: evidence as third data class (ADR 0025); units vocabulary + `Quantity` (R-11, #1213).
  §6.2: `capture` part in dataset contracts. **New §6.3** domain + `OTH`/`TBD` + companion text
  (maps to catalog class / `undecided` / unclassified; existing `OTHER` spelling mapped). **New
  §6.4** GIS schema-change process (decision-store record, patch beside it, operator rules, GIS admin
  applies via rmigis-pyt, expand-then-contract, drift check).
- §7.2: properties defined only by the catalog, never mandatory, one standard value (no per-railroad
  variants); catalog figures updated (4,054 / 6,620 / 505 rows). §7.3: `track.turnout` +
  `excluded_length` worked example; domain codes as identifiers. §7.5: SBIS uniqueness corrected to
  one row per item per bungalow with quantity; "who points at me" registry (RR Audit crosswalk).
  **New §7.6** vocabulary authority: catalog exports GIS domains through §6.4.
- **New §7A pricing module**: cost basis only (subject item or class, material/labor, unit, source
  kind, basis date, scope general/railroad/project), carry-over + override-with-reason, no overwrite,
  escalation chain to the run's valuation date, valuation logic stays in modules, double pricing
  removed by construction (#952, `prices_from=SBIS` flags), permissions + source visibility + #261,
  seeds (2019 Alstom guide, TIVS cost books) and migration of `asset_cost`/`catalog_cost`.
- §8: module table adds catalog/pricing; RR Audit stays in SBIS. **§8.1** land/sales out of scope,
  "some love" list for CVS, sales/comparables plug-in path. **New §8.2** TIVS framework + asset
  sub-modules (source + filter, data deps only, required properties/prices enforced at readiness,
  exactly-one coverage, turnout/complex trackwork example, era-mixed sources, valuation date).
  §8.3 reference hub + report production as later modules.
- §9.2 snapshot freezes valuation date, settings (#2029), sub-module/filter per record, price refs
  and index values, coverage, frames. §9.3: R-8 overtaken (#1981 is its own project).
- §10: twelve phases; phase 7 = operator places 26-150 data in `data/`; pricing (8) before SBIS (9);
  TIVS framework first then sub-modules. §11: risk 1 replaced with `rebuild:replay` label + PR line +
  PARITY.md (R-14); new risks: pricing grain/migration, filter coverage, vocabulary drift.
- §12: R-7 split into R-7a catalog / R-7b pricing; added R-11..R-14 and R-13a (empty
  `to_complex_type`: proposed undecided; today `!= NML` keeps NULLs, `tivs/assets/types.py:84`).
- `docs/PARITY.md` header now states the mechanism.

**Checked in source this run:** `tivs/assets/turnout.py:320`, `turnout_complex.py:194`,
`assets/types.py` RowFilter NULL semantics, `assets/exclusions.py`, `assets/cost_tables.py`
(`prices_from=SBIS`), `costing/models.py` AssetCost, `rcn/pricing.py` CostBook,
`sbis/costing/models.py` CatalogCost, `valuation/frames.py` STAGES, `rmi_trk_to_complex_type`
domain, `rmi-sbis-extract/conf/sources.tsv`, issues #952, #1213, #1302.
**Not verified:** how cleanly cost-book identities map to catalog classes; Survey123 field use.

**Next run should know:** the next PLAN item is behind `CHECKPOINT architecture`; wait for
`approvals/architecture.md`. After approval, turn §10 into Phase 1 tasks.

## 2026-10-02 21:14 UTC runner — waiting

Runner: waiting at checkpoint 'architecture' (approvals/architecture.md missing).

## 2026-10-02 0.9 — done

**Task**: Inventory the Survey123 form definitions the operator placed in `data/survey123/` (read
README first; forms predate schema changes). Per form: layer it writes, every question with type,
choice list, constraint, free text fields, OTHER/other escapes, disagreements with current
templates and gis-schema-review.md. Summarize what PROPOSAL §6.3 would change in each 26-150
form. The two 26-210 forms (Subject, Comparable) are land valuation, out of scope: inventory for
record, no proposals. Do not copy client-identifying content into the repo.

**What I did**:
1. Read MISSION.md, AGENTS.md, PLAN.md, JOURNAL.md, and the task requirements.
2. Examined `data/survey123/README.md`: 14 XLSForm files (12 for 26-150 track inspection, 2 for
   26-210 land valuation), placed by operator 2026-10-02, not updated since schema 2 changes
   post-inspection.
3. Built an XLSX extraction tool (Python zipfile + XML parsing) to read XLSForm structure
   (survey sheet, choices sheet, settings sheet, cell references handling sparse grids).
4. Extracted form metadata from all 14 forms: form ID, title, question counts, choice list counts.
5. Analyzed the structure of XLSForm sheets: `type` (geopoint, text, select_one, etc.), `name`
   (field name), `label` (display label), `hint`, `appearance`, `required`, `constraint`, 
   `bind::esri:` attributes, choice lists with list_name → (value, label) pairs.
6. Cross-referenced form fields against:
   - `~/sources/rmigis-pyt/templates/` (current track improvement YAML schemas)
   - `docs/inventory/gis-schema-review.md` (findings and proposals #1–10)
   - `docs/architecture/PROPOSAL.md` §6.3 (domain + OTH/TBD + companion text pattern)
7. Identified free-text fields, domain codes with escape patterns, numbered slot groups
   (switch1..6, point1..4, frog1..3, etc.), and `has_*`/`*_cnt` derived flags per form.
8. Assessed each 26-150 form's readiness for §6.3 retrofit: which domain fields need `OTH` +
   companion text, which need slot normalization, which align with current practice.

**Result**: Created `docs/inventory/survey123.md` (~650 lines, no client PII) covering:
- README caveats and method statement.
- 12 × 26-150 forms: Bungalow, Crossing, Derail, Generator, Rail, Signal, Tank, Turnout
  (Complex), Turnout CX (MPF), Turnout CX (Slip), Wayside Det (ontrk), Wayside Det (offtrk).
  Each with: layer name, design summary, key fields, disagreements with templates,
  free-text + OTHER patterns, PROPOSAL §6.3 retrofit needs (add OTH + text, slot normalization).
- 2 × 26-210 forms: Subject, Comparable. Inventoried for record (row count, choice count);
  **no design proposals** (out of scope, tabled per MISSION.md, PROPOSAL §8.1).
- Cross-form summary table: free-text patterns (make/model, notes, etc.), `OTH` usage (where
  structured, where missing), numbered slots, derived flags.
- Slot normalization priority: Crossing (medium) and Turnout variants (high, PROPOSAL #1 worked
  example, §8.2).
- GIS schema-review overlaps: which of 10 proposals apply to forms (slot normalization, envelope,
  derived facts, identity links, domains, constraints).
- Recommendation for next run (phase 7 after approval): validate live layer drift, apply form
  updates for §6.3 retrofit, test sync contracts on real 26-150 data.
- File paths: all 14 forms, source templates, schema review, GIS inventory, PROPOSAL.

**What I found**:
- **Free-text and escape patterns**: Forms use free TEXT for make/model (`*_mfr`), notes (`notes_*`),
  and some domain fields. `OTHER`/`OTH` escape exists in some domains (e.g., `bglw_use` → SIG_OTH)
  but is unstructured: no dedicated companion text field pattern in most forms.
- **Domain fields needing §6.3 retrofit**: ~20 fields across all forms lack proper `OTH` + text
  (bungalow use/class/material/condition; crossing gate/flasher/cantilever types; signal
  aspect/lamp types; turnout subtypes; wayside detector type; derail type; rail profile if free).
- **Numbered slots (highest impact)**: Crossing (4+ gates, 3+ flashers, ~36 columns) and Turnout
  variants (27 groups, ~200 columns) define PROPOSAL #1 (normalize to child rows on sync).
  Forms are the capture contract; schema 2 YAML and live layers must match.
- **Derived facts**: All forms use `has_*` and `*_cnt` fields; sync should compute and report
  disagreement (PROPOSAL #3), not trust stored values.
- **Identity joins**: All forms use `rel_*` asset ID text fields; sync should resolve to GlobalID
  edges (PROPOSAL #4), not query on text.
- **26-210 forms** (Subject, Comparable): minimal inventory (25 and 100 questions respectively);
  land valuation out of scope; no proposals. Both forms must be preserved as capture contracts
  for eventual sales/comparables module (PROPOSAL §8.1, "plug-in path later").

**Not checked**:
- Live Portal layer drift (schema 2 slot migration status, field presence, domain codes, enum escapes).
- Cascading selects (`choice_filter` expressions), branching logic (`relevant`), appearance flags,
  media (audio, image) in detail.
- Field type mismatches between form and Portal layer (text vs. numeric, length, domain adherence).
- Collected data (.gpkg files, real instances); forms define contract, validation is sync-time.

**Next run should know**:
- Task 0.9 complete; survey123.md inventory ready.
- Key uncertainty: are Crossing and Turnout slot columns still in live layers, or migrated to
  related tables? This determines whether sync slot-normalization is needed (PROPOSAL #1).
- §6.3 retrofit is form-side only (no Portal schema change); add `OTH` + companion text fields
  to domain questions. Timing: phase 6 (publish GIS domains) or phase 9 (SBIS port prep).
- Phase 7 (26-150 data arrival): validate data against form contract, test sync slot
  normalization on real records.
- PROPOSAL §10 mentions Survey123 forms in phase 6 (domain finalization) and implicitly in phase 7
  (data validation); task 0.9 confirms readiness.


## 2026-10-02 22:17 UTC runner — waiting

Runner: waiting at checkpoint 'architecture' (approvals/architecture.md missing).

## 2026-10-02 1.0 — done
**PROPOSAL.md.** Read `approvals/architecture.md`. Replaced §12 ("for the operator to rule on") with
"Operator rulings": every R-n marked ruled with his answer (all accepted; R-8 noted as overtaken; R-6
with the measured slot figures; R-7b keep scope general/railroad/project; R-12 with `OTHER`→`OTH`,
`UNK`/`UNKNOWN`→`TBD`, own companion text per field shown only on `OTH`/`TBD`, no `or_other`; R-13a
= undecided, unassigned, blocks valuation; R-14 `rebuild:replay` label used from now). Added the
cost-index decision (default per catalog domain, overridable per project with a reason, decided in
the pricing phase) and his note that `docs/inventory/survey123.md` is unreliable. Two other edits
only: the header line about rulings, and the R-13a sentence in §8.2 (now states the ruling). Rest
untouched.

**PLAN.md.** Build order §10 became tasks. Ids are `B<n>` for phase n (so they do not collide with
Phase 0/1 numbering). **B1** (harness and contract) is 21 small tasks, B1.1–B1.21: toolchain
(standard; box has python 3.14, no pip/uv found, so B1.1 must find out and list what is missing),
CI checks (file size, core-is-clean, module isolation), test DB harness, `Ref`, manifest (the one
heavy code task), resolve, loader, describe, template + `hello`/`hello_friend`, contract-test helper,
migrations check, decision store + ADR import, MAP.md/ADDING_A_MODULE.md, and a heavy phase review.
Local tiers for single-file code units with tests. **B2–B6** and **B8–B12** are one placeholder each
(standard), to be broken down when reached; B6 carries the parser redo of the Survey123 inventory.
Gates are their own CHECKPOINT lines: **`real-data`** (`approvals/real-data.md`, before B7, the 26-150
data; Survey123 forms need no gate) and **`cutover`** (`approvals/cutover.md`, before B13 cutover
planning). Verified the runner parses the plan (`runner/test_run.py` passes; first task is B1.1).

**Next run should know.** B1.1 first. No code exists yet; if the box has no PostgreSQL or uv, B1.1
should say so in `docs/TOOLCHAIN.md` and B1.6/B1.15 will block until the operator provides one.
I did not check the box's toolchain beyond `python3 --version` (3.14.4, no pip) and `which`.

## 2026-10-02 B1.1 — done
**Found** (full table in `docs/TOOLCHAIN.md`): system python 3.14.4 with no pip or ensurepip; no
python 3.12, uv, make, ruff, pyright, pytest; docker present but `rebuild` is denied the socket; no
PostgreSQL anywhere; no sudo. PyPI, GitHub and `apt-get download` are reachable.
**Did** (all user-level, no root): installed uv 0.12.22 and Python 3.12.15 (via uv) and `make` 4.4.1
(`apt-get download` + `dpkg -x`) into `~/.local/bin`. Chose a **uv workspace** (old platform's
layout, one lockfile, per-module packages for the `rmi.modules` entry point). Created root
`pyproject.toml` (python `>=3.12,<3.13`; ruff, pyright strict, pytest + pytest-asyncio auto mode),
`Makefile` (`make check` = sync, ruff check + format check, pyright, pytest), `.gitignore`,
`core/pyproject.toml` + `core/src/rmi_core/__init__.py` (empty workspace member), `contracts/`,
`modules/`, `scripts/` (with `.gitkeep`), `tests/test_toolchain.py` (two trivial tests), committed
`uv.lock`. `make check` is green, also under `env -i PATH=/usr/bin:/bin ~/.local/bin/make check`.
**Next run should know.**
- `make` and `uv` live in `~/.local/bin`, which is **not** on the runner's PATH (`runner/run.py` adds
  only `~/.local/node/bin`). The Makefile adds it for `uv`, but call `~/.local/bin/make check` (or the
  operator adds that dir to the runner's PATH / installs make). Runner not edited (out of task).
- **PostgreSQL is missing.** I verified `pgserver` (PyPI, PG 16.2, no root, no PostGIS) starts via
  uv. I amended B1.6 in PLAN to try it before blocking. Operator options are in TOOLCHAIN.md. B1.15
  needs a database too.
- pyright runs strict over `core contracts modules scripts tests`, with `extraPaths = ["core/src"]`;
  ruff skips `docs`, `runner`, `data`. Ruff/pyright were newer than the old platform's pins (0.16,
  1.1.414); lockfile holds them.
- `modules/*` is a workspace glob, `_template` excluded; `modules/` is empty now, so B1.12 should
  keep the template out of the workspace and out of pyright (already excluded in the config).

## 2026-10-02 22:42 UTC B1.2 — runner

Runner: ended without finishing (exit 0), attempt 1 of 3.

```

```

## 2026-10-02 B1.2 — done

Implemented file size check for .py files (>500 lines) in core/, contracts/, modules/, and scripts/. Added scripts/check_file_size.py and tests/scripts/test_check_file_size.py, and integrated it into make check.

## 2026-10-02 B1.3 — done

Implemented core-is-clean check in scripts/check_core_clean.py and tests/scripts/test_check_core_clean.py. Wired into Makefile via check-core-clean target and make check.

## 2026-10-02 22:55 UTC B1.4 — runner

Runner: ended without finishing (exit 0), attempt 1 of 3.

```

```

## 2026-10-02 23:05 UTC B1.4 — runner

Runner: ended without finishing (exit 0), attempt 2; re-tagged from coder to standard after 2 failed local runs; attempts reset.

```

```

## 2026-10-02 B1.4 — done

Rewrote `scripts/check_module_isolation.py` (the local attempts' version diffed the working tree only and its tests patched `sys.exit` wrongly) and its test. `check_module_isolation.py <base-ref> --module <key>` fails (exit 1) on any changed path outside `modules/<key>/`, `contracts/<key>_*`, `docs/`. Changed = `<base>...HEAD` plus uncommitted and untracked files; renames count as delete + add so moving a file out of a module is caught. Exit 2 on a bad ref or a malformed key. Tests build real temp git repos (10 cases).
- Wiring: `make check-isolation BASE=<ref> MODULE=<key>` (not part of `make check`, which has no arguments) and `.github/workflows/module-isolation.yml`: on pull requests from branches named `module/<key>[/...]` it runs the check against the PR base SHA; other branches skip it. B1.5 should create `ci.yml` separately for `make check`.
- Convention introduced: module work happens on `module/<key>` branches.
- The new files pass ruff and pyright strict. `make check` is NOT green: pyright reports errors already present in `scripts/check_file_size.py`, `scripts/check_core_clean.py` and their tests (B1.2, B1.3; untyped `main()` and test fixtures). Next run should fix those (a coder/standard task is worth adding before B1.5 so CI can be green).

## 2026-10-02 23:14 UTC B1.4 — runner

Runner: the task was ticked but `make check` failed, so it is un-ticked (attempt 1). The next attempt starts from this commit.

```
  /home/rebuild/work/rmi-platform-next/tests/scripts/test_check_file_size.py:31:47 - error: Type of parameter "tmp_project" is unknown (reportUnknownParameterType)
  /home/rebuild/work/rmi-platform-next/tests/scripts/test_check_file_size.py:31:47 - error: Type annotation is missing for parameter "tmp_project" (reportMissingParameterType)
  /home/rebuild/work/rmi-platform-next/tests/scripts/test_check_file_size.py:32:5 - error: Type of "write_text" is unknown (reportUnknownMemberType)
  /home/rebuild/work/rmi-platform-next/tests/scripts/test_check_file_size.py:33:28 - error: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/rebuild/work/rmi-platform-next/tests/scripts/test_check_file_size.py:36:47 - error: Type of parameter "tmp_project" is unknown (reportUnknownParameterType)
  /home/rebuild/work/rmi-platform-next/tests/scripts/test_check_file_size.py:36:47 - error: Type annotation is missing for parameter "tmp_project" (reportMissingParameterType)
  /home/rebuild/work/rmi-platform-next/tests/scripts/test_check_file_size.py:37:5 - error: Type of "write_text" is unknown (reportUnknownMemberType)
  /home/rebuild/work/rmi-platform-next/tests/scripts/test_check_file_size.py:38:28 - error: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/rebuild/work/rmi-platform-next/tests/scripts/test_check_file_size.py:41:42 - error: Type of parameter "tmp_project" is unknown (reportUnknownParameterType)
  /home/rebuild/work/rmi-platform-next/tests/scripts/test_check_file_size.py:41:42 - error: Type annotation is missing for parameter "tmp_project" (reportMissingParameterType)
  /home/rebuild/work/rmi-platform-next/tests/scripts/test_check_file_size.py:42:5 - error: Type of "write_text" is unknown (reportUnknownMemberType)
  /home/rebuild/work/rmi-platform-next/tests/scripts/test_check_file_size.py:43:28 - error: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/rebuild/work/rmi-platform-next/tests/scripts/test_check_file_size.py:46:5 - error: Type of "unlink" is unknown (reportUnknownMemberType)
  /home/rebuild/work/rmi-platform-next/tests/scripts/test_check_file_size.py:47:5 - error: Type of "write_text" is unknown (reportUnknownMemberType)
  /home/rebuild/work/rmi-platform-next/tests/scripts/test_check_file_size.py:48:28 - error: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
  /home/rebuild/work/rmi-platform-next/tests/scripts/test_check_file_size.py:51:5 - error: Type of "unlink" is unknown (reportUnknownMemberType)
  /home/rebuild/work/rmi-platform-next/tests/scripts/test_check_file_size.py:52:5 - error: Type of "write_text" is unknown (reportUnknownMemberType)
  /home/rebuild/work/rmi-platform-next/tests/scripts/test_check_file_size.py:53:28 - error: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
43 errors, 0 warnings, 0 informations
make: *** [Makefile:23: typecheck] Error 1
```

## 2026-10-02 23:25 UTC B1.4, B1.4b — operator housekeeping

B1.4 (Sonnet, after two failed local attempts) was correct and passed ruff and pyright strict on its own
files; the runner's new `make check` gate un-ticked it for pyright errors left in B1.2/B1.3's files, which
the earlier housekeeping had fixed for ruff only. Those files now carry type annotations (behaviour
unchanged), `make check` is green on rmi-nuc (19 tests, both checks), and B1.4 and B1.4b are ticked.
Lesson for the runner: the gate is only fair once the tree is green, so housekeeping must leave `make
check` passing, not just one tool.

## 2026-10-02 23:22 UTC B1.5 — runner

Runner: ended without finishing (exit 0), attempt 1; retrying now.

```

```

## 2026-10-02 23:23 UTC B1.5 — runner

Runner: ended without finishing (exit 0), attempt 2; re-tagged from drudge to light after 2 failed local runs; attempts reset; retrying now.

```

```

## 2026-10-02 B1.5 — done

**Task**: GitHub Actions workflow running `make check` on push and pull request (Python and tool versions from docs/TOOLCHAIN.md).

**What I did**:
1. Read MISSION.md, AGENTS.md, PLAN.md and JOURNAL.md to understand context.
2. Reviewed docs/TOOLCHAIN.md to identify the required tool versions:
   - Python 3.12 (per ADR 0002, as recorded in TOOLCHAIN.md after B1.1)
   - uv 0.12.22 (the version installed on rmi-nuc during B1.1)
   - make 4.4.1 (available on rmi-nuc in ~/.local/bin, but may or may not be on GitHub Actions runners)
3. Examined the existing Makefile to understand `make check` target:
   - Runs: sync, lint, typecheck, test, check-size, check-core-clean
   - Exports PATH to include ~/.local/bin for uv and make
4. Reviewed the existing module-isolation.yml workflow for GitHub Actions patterns.
5. Created `.github/workflows/ci.yml`:
   - Triggers on: push to main, and all pull requests
   - Sets up Python 3.12 with actions/setup-python@v5
   - Installs uv 0.12.22 using astral-sh/setup-uv@v3
   - Ensures make is available (check which make, install if needed)
   - Runs `make check` as the gate (lint, format-check, types, tests, checks)
6. Committed the workflow.

**What I found**:
- The Makefile already implements `make check` correctly, exported PATH for tools in ~/.local/bin.
- TOOLCHAIN.md documents the exact versions: Python 3.12, uv 0.12.22, ruff 0.16, pyright 1.1.414, pytest 9.1.
- The workflow uses the astral-sh official uv action instead of manual tarball extraction (cleaner, more reliable).
- GitHub Actions ubuntu-latest typically has make pre-installed, but the install check ensures compatibility.

**Result**: Created `.github/workflows/ci.yml` that:
- Sets Python to 3.12 (per ADR 0002 in TOOLCHAIN.md)
- Installs uv 0.12.22 (the version tested on rmi-nuc)
- Ensures make is available
- Runs `make check` as the gate on every push to main and PR

**Next run should know**:
- B1.5 is done; the workflow is committed and ready.
- All B1 harness tasks up to B1.5 are complete.
- Next phases require database setup (B1.6) and module framework implementation (B1.7 onwards).

## 2026-10-02 B1.6 — done

**What I did**: test database harness in `tests/harness/`, documented in `docs/TESTING.md`.
- `psql -d rmi -c 'select 1'` works (PostgreSQL 18.6, role `rebuild`, CREATEDB, peer auth); no block.
- `tests/harness/db.py` (helpers: scratch DB create/drop WITH FORCE, `discover_chains`, `upgrade`
  runs `alembic upgrade head` per chain), `tests/harness/plugin.py` (fixtures `migration_chains`,
  `scratch_database_url` session/sync, `db_engine` and `db_session` function-scoped), root
  `conftest.py` loads the plugin. `db_session` joins an outer transaction with
  `create_savepoint`, so tests may commit and everything rolls back.
- `pyproject.toml`: `asyncio_mode=auto`, fixture and test loop scope both `function`, `-p no:anyio`,
  `pythonpath=["."]`, pytest-asyncio >=1.0. `core/pyproject.toml` now depends on sqlalchemy[asyncio],
  asyncpg, alembic (uv.lock updated).
- Schema comes only from Alembic chains; a test fails if any `.py` calls `create_all`. The harness
  tests use their own sample chain (`tests/harness/sample_chain/`) via an overriding `migration_chains`.
- If the server is unreachable the DB tests skip; `RMI_REQUIRE_DB=1` makes them fail (verified both).
- `docs/TOOLCHAIN.md` updated: PostgreSQL no longer missing. `make check` green (30 tests, pyright strict clean).

**Next run should know**:
- Chain convention (docs/TESTING.md): `<pkg>/migrations/{env.py,versions/}`, URL from
  `config.attributes["url"]`, version table `alembic_version_<chain>`. B1.15 can reuse `tests/harness/db.py`.
- CI (`ci.yml`) has no PostgreSQL service, so DB tests skip there; set `RMI_TEST_ADMIN_DSN` and
  `RMI_REQUIRE_DB=1` when it gets one (operator follow-up, noted in TESTING.md).
- PostGIS not checked or used; B3 decides.

## 2026-10-02 23:29 UTC B1.7 — runner

Runner: ended without finishing (exit 0), attempt 1; retrying now.

```

```

## 2026-10-02 B1.7 — done

Implemented Ref type in core/src/rmi_core/refs.py and tests in core/tests/test_refs.py. Supported gis:, oid:, and module.kind: forms.

## 2026-10-02 B1.8 — done

**What I did**: the module contract.
- `core/src/rmi_core/manifest.py`: `ModuleManifest` (pydantic `BaseModel`, strict, `extra="forbid"`,
  frozen) and its parts as pydantic dataclasses so manifests read as in PROPOSAL §3.2
  (`SeamRef("catalog.items", ">=1,<2")`): `SeamRef` (with `accepts(version)`), `SeamImpl`, `Nav`,
  `Permissions` (facets, capabilities, `AccessKey`s for "a key that is a permission, not a place",
  `always_on`), `Slot` (identity `globalid|objectid`, `writable_fields`), `Job` (optional 5-field
  cron), `On`, `LinkKind` with identity `GisFeature | OidFrame | Owned` (discriminated), `Relation`,
  `Card` (`grant="host"|"own"`), `CatalogRef`; `Router` protocol (anything with `routes`).
  Version ranges: `parse_version`, `parse_range`, `range_contains` (clauses `>= > <= < ==`, AND).
  Lists are stored as tuples; callables are excluded from the JSON dump and shown by dotted name
  (`Job.name`, `SeamImpl.impl_name`, ...) so `describe` (B1.11) can dump `model_dump(mode="json")`.
- Single-manifest checks in the model: reserved keys, own names prefixed `<key>.`, paths under
  `/<key>/`, duplicates, seam both required and used, consuming its own seam, facets used by nav or
  links must be declared, `writable_fields` needs capability `gis.write_back`, `db_schema` and
  `migrations` together, `catalog_refs` tables inside the module's schema.
- `core/tests/test_manifest.py`: 37 tests (good manifest, minimal manifest, JSON form, JSON Schema,
  ranges good/bad, 19 bad manifests each matched to its message, bad parts). Invented module keys
  (`shed`, `parts`, `planner`, `viewer`) because core must not name real ones.
- `docs/CONTRACT.md`: one page, each field, what the module gets only by declaring it.
- `make check` green (74 tests, pyright strict clean).

**Deviations from the §3.2 sketch**: `schema=` is `db_schema=` (pydantic `BaseModel.schema` clash);
`accent` is a closed `Literal` list; `cards_offered` added (the sketch only had `cards_hosted`;
§4.4 needs the offering side); settings keys / config surfaces left for B2 (noted in CONTRACT.md).

**Found**: the Makefile's `check-size` target has no recipe, so the 500-line cap never runs in
`make check`; added B1.20b [drudge] to fix it.

**Next run (B1.9) should know**: cross-manifest checks (unsatisfied `requires`, `uses` reasons,
duplicate keys, cycles, `core_revision`) belong in `resolve.py`; use `SeamRef.accepts(version)` and
`SeamImpl.version`.

## 2026-10-02 23:55 UTC B1.9 — runner

Runner: ended without finishing (exit 0), attempt 1; retrying now.

```

```

## 2026-10-02 23:56 UTC B1.9 — runner

Runner: ended without finishing (exit 0), attempt 2; re-tagged from coder to standard after 2 failed local runs; attempts reset; retrying now.

```

```

## 2026-10-02 B1.9 — done

**What I did**: rewrote `core/src/rmi_core/resolve.py` (an untested draft from the failed local runs
was there; I replaced it) and added `core/tests/test_resolve.py` (14 tests). `make check` green (88 tests).
- `resolve(manifests, *, core_revision=None) -> Resolution(load_order, disabled, providers)`; pure.
- Rejects, with one `ResolutionError` (a `ValueError`; `.problems` lists every reason): duplicate
  module keys, duplicate seam offers, `requires` unsatisfied ("module 'shed' requires seam
  'parts.items' '>=1,<2', but no loaded module offers it" / "...but 'parts' offers version '2.0'"),
  `core_revision` range not containing the core's (only checked when the caller passes it), cycles
  (message names the modules left in the cycle).
- `uses` absent or out of range -> `DisabledFeature(module, seam, range, reason)`; the module still
  loads; an unsatisfied `uses` adds no edge, a satisfied one orders provider first and can form a cycle.
- Order: providers first, ties by key, so it does not depend on input order.

**Next run (B1.10) should know**: `load_modules()` should call `resolve(manifests, core_revision=...)`
and keep `Resolution.disabled` for `describe` (B1.11) and the contract test (B1.14); `providers`
maps seam name -> module key. Duplicate seam offers cannot be built from one manifest (the model
forces the `<key>.` prefix), so that branch is defensive and untested.

## 2026-10-02 23:58 UTC B1.10 — runner

Runner: ended without finishing (exit 0), attempt 1; retrying now.

```

```

## 2026-10-02 23:59 UTC B1.10 — runner

Runner: ended without finishing (exit 0), attempt 2; re-tagged from coder to standard after 2 failed local runs; attempts reset; retrying now.

```

```

## 2026-10-02 B1.10 — done

**What I did**: rewrote `core/src/rmi_core/loader.py` and `core/tests/test_loader.py` (11 tests; an
untested draft from the failed local runs was there, with a test that failed). `make check` green (99 tests).
- `load_modules(*, core_revision=None) -> LoadedModules(manifests, resolution)`; `.keys` (load order),
  `.disabled` (unsatisfied `uses`), `.get(key)`. `manifests` is a tuple in load order, providers first.
- Discovery: `importlib.metadata.entry_points(group="rmi.modules")`; `ENTRY_POINT_GROUP` is exported.
  Each entry point loads to a `ModuleManifest` (an object, e.g. `rmi_hello.manifest:MANIFEST`).
- Load problems (import failure, not a `ModuleManifest`, entry-point name != manifest key) are
  collected and raised together as one `ResolutionError` naming each entry point, then `resolve`'s
  own errors follow for the rest (duplicates, unsatisfied `requires`, cycles, `core_revision`).
- Rule I chose: **the entry point name must equal the manifest key**, so `pip`-level metadata and the
  manifest cannot disagree.

**Next run (B1.11, B1.14) should know**: `app.py`/`worker.py` do not exist yet; they must call
`load_modules()` and nothing else to find modules. `LoadedModules.resolution.providers` maps seam ->
module key. Tests patch `rmi_core.loader.entry_points`; no module package is installed yet, so the
real-discovery test only checks the empty case (B1.13's `hello` modules will be the first real entry
points, declared in their own `pyproject.toml`).

## 2026-10-03 00:33 UTC B1.11 — runner

Runner: ended without finishing (exit 0), attempt 1; retrying now.

```

```
