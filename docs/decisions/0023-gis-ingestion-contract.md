---
status: ruled
kind: architecture
date: 2026-08-14
refs: []
source_status: "Accepted (2026-08-14) · **Refines**: ADR 0016 (gives its posture"
imported_from: rmi-platform/docs/adr/0023-gis-ingestion-contract.md
imported_on: 2026-10-03
---
# 0023 — GIS ingestion: one fetch, loud derivation, explicit sync control, durable identity

**Status**: Accepted (2026-08-14) · **Refines**: ADR 0016 (gives its posture
the ingestion mechanism it asserts) · **Retires**: ADR 0007's GIS clauses to a
historical record (its 2026-07-23 amendment already superseded four of them;
this ADR states the contract that replaces the rest) · **Informed by**: the
access-path inventory #408 (`docs/reviews/GIS_ACCESS_PATHS_2026-08-14.md`),
the #451 derivation spike (`98b108bf`), and owner decisions of 2026-08-14
on #1059 and #1061.

This is a decision **record**: every decision below was taken 2026-08-14 (or
earlier, where dated) in the owner's words on the linked issues. The record
consolidates them so they stop living only in comment threads.

## Context

ADR 0016 (Accepted 2026-07-28) settled the *posture* — broad reads, DB-first,
one Portal fetch per layer, narrow guarded writes. ADR 0007 holds the
*mechanics* — client, catalog, contracts/landing, `/admin/gis` binding. Neither
states an **ingestion contract**: who fetches, on what cadence, into which
store, what a consumer may assume about freshness, and what identity links
records across stores. The 2026-08-14 audit measured the consequences of that
absence:

- **The double fetch is structural and growing.** 11 layers on 26-150, 9 on
  25-320, 3 on 26-160 are fetched twice per cycle — platform dataset sync plus
  a module typed sync — and every new asset family adds one, because
  `get_binding` resolves dataset-declaring slots through the *same* binding row
  the platform sync uses (one binding, two fetches; binding-table joins find
  only 2 of it).
- **Valuation reads the staler store.** The platform copy refreshes on a daily
  cron; the typed copies TIVS and CVS value from refresh when somebody
  remembers. Measured drift: 19 days on 25-320, always running *against* the
  number being produced.
- **Nothing scopes sync per project.** `scheduled_gis_resync` syncs every
  bound dataset of every project, no filter — a delivered project's platform
  store tracks whatever GIS says, daily, with nobody asking. The 19-day drift
  is currently the *only* thing keeping a GIS edit out of 25-320's valuation
  basis, and it does that job by neglect.
- **SBIS keys ~3,465 references on the mutable `asset_id`** while the platform
  and both other modules already land the durable GlobalID (100% of
  `gis_dataset_row.feature_id` across all 15 datasets are real GlobalIDs).
  Renaming an asset in GIS silently orphans SBIS rows.

## Decision

### 1. One Portal fetch per layer; module typed syncs derive from the platform store

The platform dataset sync is the **only** fetcher of a bound layer. Module
typed syncs (TIVS's 14 sources, CVS's subject segments) become **derivations**
from `platform.gis_dataset_row` — transform locally, never re-query the
Portal. ADR 0016 §2's constraints carry over unchanged: the platform sync is
standalone and complete by itself; derivations are optional subscribers that
run only where the module is enabled; a dataset with no subscriber is
legitimately synced.

Proven feasible by the #451 spike (`98b108bf`, run against production): 114
fields reconstructed from the stored layer schema, contract validation with
**zero** schema errors, row counts matching the live fetch (429/429, 245/245),
674/674 rows joining by GlobalID. `FieldInfo` round-trips losslessly because
the platform stores the whole field record — name, type, alias, length,
coded-value pairs.

Trigger semantics follow the owner's 2026-08-07 direction on #451: **a sync is
a sync, platform-wide** — one project-wide act, platform landing first, then
derivations, rather than per-module syncs a user must know to run in sequence.

**"Only" became structural on 2026-09-02** (#1077, the end state #451 deferred). Until then the
module-side live fetch survived behind a per-project flag, so this section was
enforced by a default rather than by the code. `fetch_from_portal` and the flag
are now gone from both modules: there is no second path to opt into. What made
the removal safe to take in one step was measurement rather than the elapsed
window — every inventory contract had named a dataset since #1107 (14/14 TIVS
sources, all 24 era-variants, plus CVS), no project had opted out, and every
bound dataset was verified to derive against production first.

### 2. A derivation must refuse loudly — deriving has failure modes fetching does not

A fetch either succeeds or throws. A derivation can read an apparently-good
snapshot that is not a legitimate basis — every mode below observed or
produced against production data:

| failure mode | why the snapshot lies |
| --- | --- |
| dataset **not bound** | synced rows and run history outlive their binding (26-160 holds 13 `crossings` rows plus a succeeded run, no binding) |
| **no successful platform sync** exists for the dataset | there is no basis at all — nothing legitimate to derive from |
| newer sync's **full-refresh DELETE** removes the selected run's rows mid-read | valid schema, empty row list |
| run **fetched features but landed none** (no usable identity) | still recorded as succeeded |
| run **captured no layer schema**, or predates captured coded-value pairs | no contract check is possible; labels land empty across the 14 typed tables that store them (live case: 26-160 crossings, run 39) |
| the binding **moved to another layer** since the run (#1546) | valid rows, correct dataset name, wrong layer. The run records `layer_ref` (`service/type/layer`) and the derivation compares it with the binding; a run older than the column falls back to the binding's `updated_at` against the run's `finished_at` |

Each must be a refusal with a reason, never an empty result: **an empty typed
table is indistinguishable from a layer with no features**, so a derivation
that cannot prove its basis legitimate must fail loud (the platform's standing
fail-loud rule, and #899's principle — absence must be an answer, not an
ambiguity).

Two invariants make the basis provable (both spike-proven, recorded in
`docs/runbooks/gis-sync-landscape.md`): **rows and schema come from one
succeeded run** — the derivation reads the latest succeeded run and exactly
the rows carrying its `run_id`, which is what closes the mid-read window and
prevents validating new rows against an older schema — and **a derived run
records its source** (`derived_from_run_id`), so "which snapshot is this
valuation built on" stays answerable after the logs rotate.

### 3. Sync control: two explicit per-project settings

| setting | governs |
| --- | --- |
| **Auto-Sync** | whether the scheduled job syncs this project |
| **Sync Lock** | a deliberate freeze: blocks auto **and** manual, **both engines** (platform + module derivations), **and write-back** |

| reachable state | scheduled | manual |
| --- | --- | --- |
| Auto-Sync on, unlocked | runs | allowed |
| Auto-Sync off, unlocked | — | allowed |
| Locked | — | blocked |

- **Explicit, never derived from lifecycle.** Delivered/closed/archived may
  *prompt* ("consider disabling sync") but must never switch it. A proxy
  cannot distinguish a decision from an accident — the same argument that made
  scope explicit in #899, one level up.
- **Engaging the lock disables Auto-Sync; releasing it does NOT re-enable
  it.** An admin who needs one deliberate sync on a delivered project unlocks,
  syncs, and lands in the middle row — without silently re-arming the nightly
  job. Re-enabling Auto-Sync is its own visible act.
- **While locked, Auto-Sync cannot be enabled at all** — the setting endpoint
  refuses (every gate is server-side; a disabled control is a courtesy, never
  the enforcement) and the toggle renders disabled showing its off state. This
  makes the safety property structural: `auto_sync = on` alongside
  `sync_lock = on` is **unreachable**, so releasing the lock can never re-arm
  the job regardless of what any transition remembered to zero. Test the
  refusal at the endpoint, not only the disabled control — they fail
  independently.
- **The lock stops write-back too** (owner, 2026-08-14). A project whose final
  value is out should not push attribute changes to GIS any more than it
  should pull them. #866's queue is asynchronous, so the lock is consulted at
  **apply** time, not only at submission — and a blocked change stays
  **queued**, never dropped, so unlock → apply → re-lock works.
- **Engaging and releasing the lock is audited** (who, when, why): it is the
  thing standing between a delivered valuation and an accidental GIS edit, and
  ADR 0021's durability posture points the same way.
- **A locked project says so** wherever someone would otherwise wonder why
  nothing updates — the sync pages, `/admin/gis`, beside valuation runs. A
  locked project must not look like a failing one.

### 4. Cadence: module derivations get the cron — but never before the toggles

Today the platform sync has a daily cron and the module syncs have none; that
asymmetry is the 19-day drift, and drift is the part that reaches a number.
Module derivations therefore get scheduled cadence, ordered platform-first
(free under §1, since derivations run from the just-landed rows).

**Ordering constraint: the §3 toggles ship first, or together with cadence —
never cadence alone.** 25-320 auto-syncs daily against a delivered valuation,
and the drift is the only thing keeping a GIS edit out of its basis;
scheduling module syncs without the switch would remove that accidental
protection and start auto-moving a delivered project's basis. Staleness stays
visible either way: surfaces show the basis ("typed sync is N days behind the
platform sync"), so the guarantee is checkable rather than trusted (#900's
earlier half).

### 5. Identity: store the GlobalID; display and write back the `asset_id`

Stored links use the **GlobalID**. The `asset_id` is for **display and GIS
write-back** — it is what GIS's `rel_*` fields hold and what an engineer
reads, resolved from the GlobalID at render time. Measured basis: 100% of
`gis_dataset_row.feature_id` values are real GlobalIDs, TIVS typed tables
carry `globalid`, and SBIS stores none of it — roughly 3,465 references on
the mutable id. Write-back (#866) carries the GlobalID as the *target* and
the `asset_id` as a *value*, never the `asset_id` as both.

**Amended 2026-09-17: the OID camera catalogs land by OBJECTID** (owner ruling;
built in #1894). No production OID layer publishes a GlobalID, and the catalogs are static, so
their OBJECTIDs are not reassigned. A dataset whose every consuming slot declares
`objectid_identity` lands under its OBJECTID when the layer has no GlobalID; only
CIV's `oid` declares it. A GlobalID still wins wherever the layer has one, and every
other dataset keeps GlobalID-or-refuse.

**The GIS link is an attribute of the SBIS record, not its identity.** SBIS
rows have their own surrogate identity (already present: `bungalow.id`), so
four operations are legitimate rather than exceptional: **create unlinked**
(surveyed before GIS knows it — a known orphan, deliberate), **link**,
**unlink**, and **relink** (the "we inventoried the wrong point" recovery).
Relink also answers delete-and-recreate — the GlobalID changes, the SBIS
record does not; contents, catalog links and relations ride along untouched.
Link changes are audited: relink moves an entire inventory between physical
assets. A pairing to third-party evidence
([ADR 0025](0025-third-party-evidence-reconciles-against-the-inventory.md) §3)
follows the same rule — it points at the record's surrogate id, rides along on
a relink, and is reviewed again when one happens.

**Orphans are a supported state with three distinct causes**, needing
different actions — and only a stored GlobalID can tell the first from the
second, since a rename under `asset_id` keying looks exactly like a deletion:

| cause | means | action |
| --- | --- | --- |
| target deleted in GIS | history | someone decides if it is still true |
| never resolved, predates the rules | free-text-era residue | correct in SBIS |
| never resolved, GIS has not caught up | **legitimate and expected** | wait; it heals itself |

Cause is judged against the latest **successful** platform sync; when that
freshness cannot be established, the cause stays unknown rather than claiming
a deletion — a stale snapshot must never turn "not synced lately" into
"deleted in GIS" (mechanism on #1061).

The free-text add-relation path **stays** — SBIS routinely knows about an
asset before GIS does — but an unresolvable reference is created as a **known
orphan** rather than stored as though it resolved (today `add_related_ref`
checks presence and duplicates, never GIS existence). Back-fill is safe by
construction: 861 of 863 existing relations resolve by joining `asset_id` →
`gis_dataset_row.feature_id`, and anything that does not resolve lands as a
known orphan — a work list, not a gate; no record can be lost.

One consolidation trap, recorded so it is not re-derived: **`sbis.status` is
not GIS `status`** — survey completion (Complete / Incomplete / No As-Built)
vs asset lifecycle (ACTIVE / OOS / OTHER). Any column-by-name merge would
silently destroy a survey workflow.

### 6. Scope semantics are one question, answered once

Inclusion scope is currently spread across three issues in three milestones,
but it is one design question and gets one answer, consistent with #899's
explicit-scope declarations:

- **`include` gates valuation, not the frame** (#898): inventory surfaces see
  non-included assets; the filter applies where the number is produced.
- **`include IS NULL` is not `include = 0`** (#1040): "nobody decided" and "we
  decided no" must not drop a record the same silent way.
- **Per-structure include on `xing_str_tbl`** (#896): scope reaches the
  structure grain, populate-first rollout.

## Non-decisions (delegated)

Mechanisms stay open on their issues: the derivation engine and its refusal
surface (#451, re-scoped to the audit's numbers; #899 is a **hard gate before
the final cutover** — unified sync makes an unbound source silently empty);
the sync-control storage/endpoints/UI (#1059); the SBIS GlobalID migration
and link-state model (#1061 — groundwork, deliberately not immediate work);
write-back mechanics (#866); the scope mechanism details (#898, #1040, #896,
and #899); curation of the five unread platform copies (#456); SBIS
request-time coupling (#452); the TIVS exhibit task's geometry need (#1042 —
the one live read with a real obstacle, not inertia).

## Consequences

- **ADR 0007 retires to a historical record.** Its four GIS clauses were
  already superseded by its own 2026-07-23 amendment; with the ingestion
  contract stated here, its remaining unique content is the mechanical layer
  (service/folder resolution, client, contracts/landing, `/admin/gis`
  binding), which moves to reference documentation as follow-up work. No new
  decision may cite 0007 as authority.
- **ADR 0016 keeps the posture; this ADR is its mechanism.** The two cannot
  silently diverge: 0016 §2's "one Portal fetch per layer" now has a stated
  owner (the platform sync), a stated consumer contract (§2 refusals), and a
  stated cadence (§4).
- **Ordering constraints are now recorded, not tribal**: toggles before
  cadence (§4); #899 before the #451 cutover; the crossing leg's slice 4
  (TIVS enumerates `xing_str_tbl`, closing #944) wants this ADR first —
  slices 2 and 3 are parallel to all of it.
- The reconcile surfaces (#462, #894, #1044) and injection inherit §5's
  identity model as they evolve; orphaned injected `signal_asset` rows are a
  stale-projection hazard (prices stay alive) wanting detection, not an
  orphan state.
- Every §2 refusal and §3 state is a testable invariant — endpoint refusals
  and derivation guards get tests, not just rendered-disabled controls.
