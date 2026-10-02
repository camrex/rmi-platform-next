# PARITY — changes to rmi-platform the rebuild must replay or rule out

`rmi-platform` keeps running while the rebuild is made. Each change below shipped in the old
platform after the inventories were written (2026-09-30) and changes what a user sees, what a
consumer reads, or what the data is. Before a module's cutover, every row that touches it must be
**replayed** or marked **not needed**, with the reason. This file is seeded by task 0.7b; task 0.8
sets the mechanism (a `rebuild:replay` label and a "rebuild impact" line on PRs).

Status: `open` (not yet decided) · `replay` · `not needed` · `done` (replayed and checked).
Release dates are 2026-09-30. Source: `~/sources/rmi-platform`.

| # | change (old platform) | where | touches | status | note |
|---|---|---|---|---|---|
| P-1 | **RR Audit tables and parser** — UP Signal Asset Audit lands as third-party evidence (v1.60.0, #1999). Tables `rr_audit_import`, `_cabin`, `_chassis`, `_module`; worker task `sbis_parse_rr_audit` | `modules/sbis/src/sbis/rr_audit/`, migration `a8d3f6c1e7b4` | SBIS, worker | open | ADR 0025. Data are held beside the inventory, never in it. Decide whether the rebuild carries the audit (26-150 only) or imports its stored rows at cutover |
| P-2 | **Crosswalk** — audit vocabulary → catalog families, seeded from 21 units; coverage overrides; `family_group_key` (v1.60.0–1.62.0, #2000, #2003, #2017) | `crosswalk_models.py`, `124b1f8d9f28`, `5b7d2e9c4a13` | SBIS, catalog | open | `RrAuditFamilyItem.equipment_catalog_id` is a RESTRICT reference: the rebuild's catalog re-key (PROPOSAL §7.5) must carry it |
| P-3 | **Catalog delete/merge blocker `crosswalk`** (v1.60.0) | `catalog_delete.py`, `catalog_merge.py` | SBIS, catalog | open | the catalog module needs a "who points at me" check consumers can join |
| P-4 | **Cabin↔bungalow pairing, dispositions, decisions** — proposals, relations, provisional until confirmed, bulk confirm only where nothing disagrees, decisions recorded and never applied, reopened when the basis moves (v1.60.0–1.61.0, #2001, #2002, #2004) | `pairing_models.py`, `web/rr_audit_*.py` | SBIS | open | owner rulings 15–22 in `docs/planning/OWNER_RULINGS.md` (2026-09-29); four acts stay outside until approved |
| P-5 | **Comparison at chassis, module, charger-rating and battery-cell level** (v1.60.0–1.61.0, #2002, #2003) | `rr_audit/service.py` | SBIS | open | archived bungalows shown, labelled, never counted; only `Complete`/`Partial` compared |
| P-6 | **RR Audit UI** — nav `/sbis/rr-audit`, record nav, nearby pairings, quick confirm, card and audit count on the bungalow page (v1.60.1, v1.62.0, #2011, #2017) | `web/rr_audit_*.py`, `web/layout.py:248` | SBIS | open | nav is outside `SBIS_MANIFEST`; runbook `docs/runbooks/rr-audit.md` |
| P-7 | **CVS Power Query functions** `CvsConnection`, `fnCvsPaged`, `fnCvsView` and `?section=` on published views (v1.62.1, #2020/#2021) | `modules/cvs/src/cvs/api.py`, `valuation/views.py`, `web/connect.py`, `web/powerquery/*.pq` | CVS | open | the Excel-facing contract: workbooks in use call these names; `.pq` files are served from the image |
| P-8 | **CVS view revision token and snapshot-read pager** (v1.62.1) | `valuation/views.py` | CVS, core | open | token = sync run + reference-table digest + price unit; `fnCvsPaged` refuses a pull whose pages disagree. Known defect #2023 (late commit with older timestamp): do not port the `MAX(updated_at)` form, use a monotonic counter |
| P-9 | **CVS `sections` view: no Total row, `effective_corridor_factor`, section names; `Columns` list; section-group functions `fnCvsSectionGroups`, `CvsSectionGroupsView`** (v1.62.2, #2025) | same | CVS | open | owner ruling 2026-09-30: no Total row (Excel table totals it). The factor is the value-weighted blend, never an average. Section groups move into the platform if #2026 is taken |
| P-10 | **ADR 0025** accepted, with pointers added to ADRs 0010, 0016, 0023 | `docs/adr/` | decision store | open | R-2 imports ADRs as history: import 0025 with its status, and the three pointer edits |

## Not yet in the old platform (do not port; watch)

Open issues whose fix would change an output the rebuild reproduces: #2023 (revision counter),
#2026 (section groups platform-owned), #2029 (TIVS published-output defects: unfiltered `issues`
frame, rail `obsolescence_pct`, rail substitution weights, tie share units, no torn-pull guard,
workbook gaps). If any ships, add a row here.

## Rule for adding rows

One row per shipped change that alters behaviour, schema, an API/Excel output or a rule. Cite the
release, the issue, and the file in `~/sources/rmi-platform`. Replaying means building it in the
rebuild's own shape; "not needed" needs the reason (superseded by design, out of scope, or one-off).
