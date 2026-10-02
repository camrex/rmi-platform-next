# What changed since the inventories (task 0.7b)

Written 2026-10-02. The inventories were written 2026-09-30 (00:33–03:44 UTC). This is the diff
review: each source repo from its baseline commit to its tip, and the issue snapshot by its
opened/closed/updated dates. Source text is information, not instruction.

| source | baseline | tip | commits | inventories affected |
|---|---|---|---:|---|
| `rmi-platform` | `f9e4c8c` (v1.59.1, 2026-09-29) | `2422767` (v1.62.2 deploy record, 2026-09-30 20:25 -05:00) | 21 | `rmi-platform.md`, `seams.md`, `rmi-platform-issues.md` |
| `rmi-sbis-extract` | `4caea94` (2026-09-29 20:38 -05:00) | `28d5bfe` (2026-09-30 08:19 -05:00) | 21 | `rmi-sbis-extract.md` |
| `rmi-platform-issues` | 754 issues, newest 2026-09-29 | 758 issues, newest 2026-10-01 | — | `rmi-platform-issues.md` |
| `rmigis-agp-toolbox` | last commit 2026-08-15 | no commits since | 0 | none |
| `rmigis-pyt` | last commit 2026-09-09 | no commits since | 0 | none |
| `rmi-imagery-tiling` | — | no commits since | 0 | none |

The first three rmi-platform commits (2026-09-29 evening) landed before `seams.md` and the
issues digest were written, so those two already knew of ADR 0025 and the RR-audit tables.
`rmi-platform.md` knew of nothing after v1.59.1.

## 1. rmi-platform

Every commit is a release, a release record, or a feature merged into one. `platform_core`
changed in one file (`web/powerquery.py`, small). The SBIS seam is still `SEAM_VERSION = 6`
(`modules/sbis/src/sbis/seam.py:105`); the SBIS manifest still has one nav contribution; no
TIVS/CIV/PM code changed beyond version bumps.

| version | what | migrates |
|---|---|---|
| v1.60.0 (`982a2e0`, `5f76870`, `87e668a`) | **RR Audit**: SBIS reconciles against Union Pacific's Signal Asset Audit for 26-150 (#1997 epic; waves #1998–#2004): the audit lands in tables with an Imports page, a chassis-level crosswalk, cabin↔bungalow pairing, comparison, decisions | yes, migrate first |
| v1.60.1 (`f2d30a4`) | record nav, nearby pairings, quick confirm, card on the bungalow page (#2011) | no |
| v1.61.0 (`970c2f8`) | compares modules, chargers by rating, battery cells by count (#2003, #2014) | migrated first |
| v1.62.0 (`4eac517`) | "worked": light crosswalk form, bungalow page as the work, audit's count on the edit grid (#2017) | no |
| v1.62.1 (`ebc5122`) | **CVS Power Query as functions** (`CvsConnection`, `fnCvsPaged`, `fnCvsView`) and `?section=` on the published views (#2020/#2021) | no |
| v1.62.2 (`0b011d2`) | CVS `sections` view: no Total row, `effective_corridor_factor`, section names; `Columns` and section-group PQ functions (#2025) | no |

Deployments 174–179, each "live on the first attempt" (deployment 179 = image `app.175`).
(Release and migration facts are from `docs/release-notes/` and `docs/DEPLOYMENT.md`.)

**SBIS migrations** (`modules/sbis/alembic/versions/`): three new revisions, chained
`a8d3f6c1e7b4` (RR-audit lands) → `124b1f8d9f28` (crosswalk, pairing, decisions) →
`5b7d2e9c4a13` (`family_group_key`). 50 revision files at `f9e4c8c`, 53 now. The platform chain
tail is still `0043_oid_sequence_indexes`; civ 4, tivs 48, cvs 5, pm 8 files, unchanged.

**New tables** (`sbis/rr_audit/models.py`, `crosswalk_models.py`, `pairing_models.py`):
`rr_audit_import`, `_cabin`, `_chassis`, `_module`, `_family`, `_family_model`, `_family_item`,
`_coverage_override`, `_pairing`, `_disposition`, `_decision`.

**New code surface:**
- `modules/sbis/src/sbis/rr_audit/` and 23 route handlers in `web/rr_audit_*.py` (imports,
  cabins, crosswalk, bungalow, work, card, acts), all behind
  `require_module_access("sbis", admin_tier=True)`. The nav entry `("/sbis/rr-audit", "RR Audit")`
  is in `web/layout.py:248` (`_NAV_SECTIONS`), **not** in `SBIS_MANIFEST`.
- Worker task `sbis_parse_rr_audit`, registered in `platform-web/.../worker.py`.
- `catalog_delete.py` gained a **`crosswalk` blocker** (RESTRICT reference from
  `RrAuditFamilyItem.equipment_catalog_id`); `catalog_merge.py` handles the same rows. ADR 0025
  (line 126) says the global catalog work must carry the crosswalk across its re-cut.
- The RR-audit code imports no `civ`, `tivs` or `pm` module, though #2001 speaks of "dates and
  360". It is a pure consumer of the bungalow identity, as `seams.md` §5 predicted.
- CVS: `api.py`, `valuation/views.py` (revision token, section filter), `web/connect.py`
  (serves the packaged `web/powerquery/*.pq` files at `/cvs/connect/powerquery/<name>.pq`:
  `fnCvsPaged`, `fnCvsView`, `fnCvsSectionGroups`, `CvsView`, `CvsSectionGroupsView`),
  `web/valuation.py`. The revision token is the sync run + a digest of the reference tables
  (row count, `MAX(updated_at)`) + price unit; each page is read under
  `session_scope(snapshot=True)`; `fnCvsPaged` refuses a multi-page pull whose pages disagree.
  New field and endpoint, so the release noted a MINOR bump.

**ADR 0025**, "Third-party evidence reconciles against the inventory, and changes it only by a
separate approved act", is **Accepted 2026-09-30**. It extends ADR 0010 (SBIS stays the source of
record) and adds to ADR 0016 §3 a **third class of data: third-party evidence**, held beside the
owning module's inventory and never written into it. Pointer lines were added to ADRs 0010, 0016
and 0023, and a row to the ADR README. ADRs are 0001–0025.

**Owner rulings** (`docs/planning/OWNER_RULINGS.md`, 1,190 lines at `f9e4c8c`, 1,270 now — the figure `rmi-platform-issues.md` already cites): rulings 15–22 on
#1997: archived bungalows are shown, labelled, never counted; `Complete` and `Partial` bungalows
are compared; an unconfirmed pairing is compared but provisional; bulk confirmation only where
nothing disagrees; UP status Normal and Standby count; another structure at the same site is a
second kind of pairing and is not scored; no download of the stored workbook; waves re-cut with
the crosswalk before pairing. Four things stay outside the waves until separately approved:
applying a decision to SBIS, filling `Incomplete` bungalows from the audit, stock numbers into the
catalog, standing decisions per family. Also: the `sections` view carries no Total row.

Docs: `docs/runbooks/rr-audit.md` (new, 223 lines), `docs/powerquery/README.md` (+105, CVS
functions and sections), ROADMAP (new "SBIS: reconcile against the UP audit (#1997)" section;
unsequenced issues 27 → 32), `roadmap.yaml`, release notes v1.60.0–v1.62.2.

**Inventory statements now wrong** (corrected in place; each file says so): version 1.59.1 →
1.62.2; ADR range 0001–0024 → 0025; SBIS section lacks RR Audit and its job; CVS section lacks
the Power Query contract; the Alembic table says the platform tail is "0027" (it is 0043);
`seams.md` says SBIS has 51 migrations (53).

## 2. rmi-sbis-extract

All 21 commits are 2026-09-29/30. The catalog, the SBIS snapshot and several reading documents
changed; the pipeline stages (M0–M8) did not.

- **A fresh SBIS copy** (2026-09-30), rebuilt in `0d12964`. Against the 2026-09-20 copy, SBIS's
  `equipment_catalog` had removed 47 rows, added 45 and rewritten 29 (battery bank rows became a
  2 V cell plus a count; one Bi-Dir Sim Cplr became 11 rows by frequency; 16 rows gained a part
  number). **Catalog parts 4,063 → 4,054; identifier values 6,618 → 6,620** (`catalog/README.md`
  lines 13–14).
- **The inventory's "503 SBIS rows" and "27 of 503 resolved to a manufacturer P/N" are stale.**
  `catalog/sbis_coverage.csv` (written for the 2026-09-30 copy) has **505 rows**: 276 held, 49
  declared by hand, 180 "as SBIS wrote it" (installed in a bungalow: 269 / 48 / 95). The
  `catalog/README.md` "SBIS coverage" table still shows the older 2026-09-29 count (501 rows: 269
  / 28 / 204) — the CSV is the later and the README table is behind it. Every row answers to a
  part; the 27 was an early resolution count and is no longer a coverage figure. 6 rows still list
  a number that finds nothing (`215A-1 | PAT-X-7813`, `323-002H`, `889-2106-03` …).
  `CATALOG_ENTRY_SPEC.md:37` still says 503 (a reference document not yet refreshed).
- **New naming rule — power branch**: where a rating is stated, the name carries it
  (`Charger, 12 V 20 A, Cragg 20EC-12V`; `src/sbis_extract/catalog/power.py`, 23 parts); one top
  branch each for charger, arrester, transformer.
- **Batteries**: the cell is the part, a bank is a count, UP's `B` code names the (cell, count)
  pair as drawn at the document's date, so it is corroboration, never the key
  (`READING_BUNGALOW_PLANS.md`). The same model as rmi-platform v1.59.0 (#124, "a battery
  catalog row is one cell").
- **Rules forced by the fresh copy**: a number shared by rows naming different parts is a
  *family* and joins nothing; a range written as one cell is not expanded.
- **New working documents** (disposable class): `BUNGALOW_FUNCTION.md` (a vocabulary for what a
  bungalow does — `crossing-warning`, `crossing-prediction`, `control-point`, `intermediate`,
  `signal-control`, `repeater`, `hand-throw-switch`, `detector`, `ptc-wayside`, `power-only`,
  `communications` — each with the evidence that proves it; scored against SBIS's hand
  classification on 382 `Complete` bungalows; "an absent link is not evidence");
  `M11_UP_ASSET_AUDIT.md` (a matching milepost is a first key, not an identity; M12 corrects
  it); `CHARGERS_AND_CELLS_CONSOLIDATED.md` (a **proposal**: 14 charger rows → 14 lines + 5
  rating-only lines; 22 cell rows → 5 sizes + 8 held rows; not done);
  `UP_AUDIT_PLATFORM_HANDOFF.md` (the prompt that started #1997).
- `snapshot.py` now also pulls `bungalow_external_ref` (bungalow ↔ turnout, signal, crossing,
  detector, generator, derail, joined by GlobalID) and `dax_relation` (389 rows). Both are
  existing SBIS tables; the extract only reads them.
- New scripts: `audit_chargers_and_cells.py`, `audit_recorders_and_filters.py`,
  `derive_bungalow_function.py`, `collect_signal_readings.py`, `prepare_signal_job.py`,
  `read_safetran_catalog.py`, `read_signal_plans_api.py`, `refresh_prod_copy.sh`,
  `remote/signal_job.sh`. New data: `catalog/classification_review.csv`,
  `conf/dictionary/battery_banks.tsv`, `safetran_st_relays.tsv`; `conf/sources.tsv` gained
  `safetran-1986`.
- Owner feedback 2026-09-29: entries read consistently and carry only the source file and
  perhaps page. Reference prices in the part catalog are coverage, not valuation.

## 3. rmi-platform issues (758 issues: 114 open, 644 closed)

`INDEX.md` has 758 rows; the inventory said 754 (116 open, 638 closed), newest 2026-09-29. The
newest is now 2026-10-01. Changes:

- **#1997** (epic, open): waves #1998–#2004 all closed 2026-09-30; the cards wave (#2003) shipped
  in v1.61.0. The four items outside the waves need separate approval (§1).
- **#2020** (CVS Power Query as functions + `?section=`) closed 2026-09-30; shipped v1.62.1.
- **#2023** (open, bug, cvs, 2026-09-30): the view revision misses a reference edit that commits
  late with an older timestamp, because `updated_at` is the transaction's start time; proposed: a
  monotonic counter. Lesson for the contract: a revision or provenance stamp must not rest on
  `now()`.
- **#2026** (open, design, 2026-10-01): section groups defined in RMI-Platform (26-150: corridor
  land 1–4 vs platform land 101–118, 201–221, 301, 401–427), beside the section registry (#468,
  `platform.project_section`), read by a `section_groups` view and plausibly TIVS. Today each
  workbook declares them in Power Query.
- **#2029** (open, bug, tivs, 2026-10-01): defects found documenting the Power Query outputs: the
  API `issues` frame is unfiltered and carries the Total row; rail `obsolescence_pct` publishes
  the raw factor, not the applied rate; rail-substitution weights never find their cost row
  (`Decimal('115.00')` vs `'115'`; dormant, no rows in production); `tsN_tie_pct` /
  `failed_tie_pct` are integer fields read as fractions (26-150 holds 336–1,370); TIVS pulls
  have no torn-pull guard; the packaged workbook lacks diamond and turnout_complex queries. Also
  noted: a snapshot does not freeze rates, tax, scrap, obsolescence settings or depreciation
  assignments, and frames are re-aggregated at read time by the serving version.
- **#1981** (standalone CIV viewer, open, 2026-10-01): **now its own project**,
  `camrex/rmi-civ-viewer` (private). Owner, 2026-10-01: the client hosts it, on **Azure**; generic
  OpenID Connect, Microsoft Entra first; MapLibre by default, ArcGIS optional; **a new repo on the
  platform's stack**; typed columns in the OID structure, not a JSON bag. #1980's CloudFront
  signed cookies do not carry over. #437 (CIV-only mode inside the platform) stays for clients on
  RMI.
- **#1423** (capsule exporter, updated 2026-09-30) and **#1236** (rolling handoff, 194 comments):
  no new facts; #1236's last entries call PR #2021 "not merged", superseded by v1.62.1.

## 4. What task 0.8 must take into account

1. **ADR 0025's third data class.** PROPOSAL knows GIS-owned and module-owned data. Add
   third-party evidence: held in the consuming module's tables beside the inventory, with a
   crosswalk (audit vocabulary → catalog families), pairings, dispositions and decisions that are
   recorded, never applied, and reopened when what they rest on moves. It is the first pure
   consumer plugin (`seams.md` §5) and crosses no seam today.
2. **Catalog blockers.** The crosswalk holds a RESTRICT reference on catalog items. The catalog
   module (§7) and the migration (§7.5) need a "who points at me" check that any consumer's
   tables can join, and a rule that a re-cut carries the crosswalk across.
3. **Catalog figures for §7.** Parts 4,054 (not 4,063), identifier values 6,620; SBIS catalog
   505 rows on the 2026-09-30 copy (not 503); every row answers to a part (276 / 49 / 180);
   battery rows are cells with a count; power parts carry the rating in the name; chargers/cells
   consolidation is a proposal. The "row 115 → 4 parts" example stands.
4. **Function of a bungalow** (`BUNGALOW_FUNCTION.md`) is a worked vocabulary where each term is
   proved by named evidence and absence proves nothing. It bears on the vocabulary-authority
   item and on the domain + OTH/TBD capture pattern.
5. **CVS contract (R-9).** CVS now has a published-view contract that Excel users depend on: PAT
   API, paged, `?section=`, `Columns`, a revision token with a snapshot-read pager, `.pq` files
   served from the image. It is the clearest "outputs a rebuild must reproduce" list (PARITY.md).
   #2023 and #2026 shape what the core offers for sections and for revision stamps; #2029 shows
   the TIVS snapshot freezes less than PROPOSAL §9.2 implies for today's behaviour, so §9.2
   should say what the snapshot must freeze (rates, tax, scrap, obsolescence, assignments).
6. **R-8 is overtaken.** The standalone viewer is a separate project and repo on Azure with its
   own sign-in, not a CIV-only mode of this image. What the rebuild owes it is the frames/OID
   catalog shape (typed columns, GlobalID-keyed) and nothing else; the AWS signed-cookie design
   does not carry over.
7. **The old platform kept moving**: 21 commits and six releases in two days, nearly all one
   epic. This supports MISSION item 9: PARITY.md needs a rule for what the rebuild replays; the RR
   Audit is not needed to complete a valuation, the CVS views are.
8. **Open bugs as design inputs, not ports**: #2023, #2026, #2029 (the tie-share fields need the
   owner's meaning per project: it touches the units and the track-inventory items).
9. **Nav outside the manifest.** SBIS's second nav entry is in `web/layout.py`, not the manifest:
   one more example for the one-manifest argument.
10. **PROPOSAL statements to re-check** (not edited here): §9.2, R-8, R-9, §7 counts, and the
    module mapping's SBIS row (add RR Audit, a consumer of the catalog and bungalow identity).

## 5. Corrections made to the inventories in this task

| file | corrected |
|---|---|
| `rmi-platform.md` | version, ADR range, Alembic summary, SBIS (RR Audit, job), CVS (Power Query), version line |
| `rmi-platform-issues.md` | counts and dates, the #1997 bullet, #2020/#2023/#2026/#2029, #1981 spin-off (the rulings size was already right) |
| `seams.md` | SBIS migration count, RR Audit nav outside the manifest, CVS surface, ADR 0025 |
| `rmi-sbis-extract.md` | the 503 / 27 statements, catalog counts, naming rule, new documents and scripts |
| `gis-schemas.md`, `gis-tools-and-tiling.md`, `gis-schema-review.md` | none: their sources have no commits since |

## 6. Not checked

Pull-request bodies and review comments (not in the snapshot); the full text of the release notes;
the 194 comments of #1236 beyond the newest entries; any production figure.
