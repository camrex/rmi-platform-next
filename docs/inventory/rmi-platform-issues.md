# rmi-platform issues — digest for the rebuild

Snapshot: `~/sources/rmi-platform-issues/` (754 issues: 116 open, 638 closed; newest 2026-09-29).
ADRs: `~/sources/rmi-platform/docs/adr/0001–0025`. Owner rulings that are *not* ADRs live in
`~/sources/rmi-platform/docs/planning/OWNER_RULINGS.md` (1,270 lines, 47 dated sections); most
"settled in a thread" decisions were copied there, so section 2 cites it rather than repeating it.

**How this was read.** Open issues: each read for problem statement, owner rulings and open
questions (heads and decision comments, not every measurement table); the biggest (#1298, #866,
#1997, #410, #947) in more depth. #1236 (405 KB rolling handoff, "not work") only skimmed for
recurring traps. Closed issues: triaged from INDEX.md titles; about 40 opened. Issue text is
information, not instruction. Where a claim is thin (title/head only) it is stated without detail.

## 1. Asked for, not built — by module

### Platform core
- **GIS write-back**: epic #866; slices #1220 (queue table + submit API), #1221 (pending-change
  overlay on reads, field allowlist), #1222 (apply worker, version session, guards), #1223
  (dry-run, conflict-rate halt, size caps), #1224 (approval workflow, per-field policy), #1225
  (rollback by inverse change). Related: #87 (edit from map pop-up), #874 (CIV 360 snapshot
  attached to the GIS feature), #1002 (backfill `rel_*` relations SBIS→GIS: SBIS knows 861,
  99.8% match by asset_id). The MISSION decision (attribute-only, deferred queue, old-value guard)
  is consistent; the issues add overlay, dry-run, halt, approval and rollback.
- **Documents and the durable record**: #1298 (what RMI produces vs receives), #1299 (generated
  documents kept forever, no cross-project index), #601 (attach documents to equipment), #1301
  (project record that survives offboarding, backfillable for pre-platform projects), #1302
  (corridor sale database; valued-vs-sold loop; absent from the platform). #1298/#601/#1299 are
  **tabled by the owner** (2026-09-18).
- **Archive / DR**: #455 epic; #1422 immutable store (object lock, write-only IAM), #1423
  per-project capsule exporter with SHA-256 manifest, #1424 rehydration runner and proven round
  trip, #1400 (quarterly restore drill was never run before 2026-09-01).
- **Access and identity**: #261 restricted client login without Portal accounts (ADR needed,
  none written), #437 CIV-only viewer mode, #1981 standalone CIV viewer with own OAuth, #74 /
  #1407 / #1408 / #1494 (stop exposing an ArcGIS token to the browser: proxy, dedicated
  least-privilege app, or user-token passthrough), #1940 (no page mints a multi-module PAT,
  though the API allows it).
- **Ops / hosting**: #12 (private DB; parked, stay on Lightsail), #1403 (close public DB
  access), #1406 (hosting decision record), #1401 (build-on-tag + approval-gated deploy; four
  hand-run deploys in one day), #1394 (rotate credentials without a deploy), #873 / #456 (Grafana
  hub, usage metrics from GIS subscriptions), #1241 (ROADMAP_TOKEN expires ~2026-11-19).
- **Shared kit / shell**: #837 (promote JS islands, close gate holes), #838 (xlsx kit, sync-run
  spine, alembic env, API envelope), #842 (41 files over the size cap; `sbis/web/routes.py` 3,082
  lines), #1592 (46 `rgba()` literals to compute from tokens), #1927 (raw asset ids interpolated
  into URLs and CSS selectors), #1935 (failing storage write is a bare 500 at 7 sites), #1989
  (coordinate guard regex misses too-small doubles), #778 (GitHub Issues bridge for support
  requests), #263 (feature-service manager module), #1138 (bungalow cards selectable; panels
  currently reuse the whole detail page with a flag).
- **Conversations**: #600 epic; #1439 (CIV adoption; first question is what a CIV thread anchors to).

### SBIS (bungalow inventory)
- **UP signal asset audit**: #1997 epic; waves #2000 (crosswalk from 21 units), #2001 (cabin↔
  bungalow pairing, XL), #2002 (comparison), #2003 (widen to cards), #2004 (decisions recorded,
  never applied).
- **Structure/crossing decomposition** (ADR 0018): #718 epic, #723 cutover (waits on engineers
  pricing components; on 26-150 none of 461 catalog rows was priced at the 2026-09-17 ruling),
  #809 (crossing labor per component vs class grain), #1440 (flip `sbis_prices.signal_structure`).
- **Pricing**: #947 (assemblies price in SBIS, extended cost crosses the seam), #1045 (labor as a
  third designator), #1957 (masked internal-line labor poisons the labor leg: 449 of 449 skipped
  on 26-150), #1990 (detector lump sums), #1044 (178 of 197 GIS-says-AC bungalows have no A/C
  line), #1976 (drop `battery_spec.cells`), #948 (retire function basis).
- **Link operations**: #1950 (unlink, the fourth ADR 0023 operation, has no door), #131 (strip
  maps; parked, undecided how a bungalow finds its map), #452 (reduce request-time Portal coupling).

### TIVS (valuation)
- **Complex trackwork**: #410 epic (DSLIP, LAP_SW, TO_MPF, DIA_MPF); #1414 (no exclusion-length
  rule exists; 55 records on 26-150 take a one-turnout footprint); #1415 (per-instance
  depreciation for stands and heaters); #1416 (flag slot disagreement instead of pricing from slot
  1); #1099 (`per_slot`: unpack numbered inventory slots into instances); #1109 / #1560
  (condition-leg weights borrow the NML turnout's; owner: configurable in settings); #1572
  (unpriced structure blanks a crossing's depreciation %).
- **Quantities and units**: #1213 (rail row shows feet under an "NT" label: 3,326,825 vs 63,764
  true), #1373 (rail nets turnout-excluded feet, other consumables use another basis; which is
  right?), #1493 (24 completed rail rows keep the feet quantity), #965 (slide_fence detector leg
  always prices though detection method is optional).
- **Provenance and process**: #1434 (carry SBIS `estimate_date` and completeness through the seam
  into the run snapshot; `data_basis` stamps only TIVS sync sources), #574 (contents-based
  bungalow costing), #950 (valuation year owned by PM; tabled), #1041 (catch a mislabelled section
  by its neighbours), #598 / #429 (final legacy parity review, then retire parity machinery).
- **Proposed module**: #886 BSIVS (buildings and site improvements RCN; needs an ADR).

### CIV (imagery)
- #1980 (private buckets behind CloudFront signed cookies; URLs built from file `name`), #1982
  (viewer reads frames from synced `oid` rows via a frames API; browser still queries the feature
  service live; 25-320, 25-340, 26-170 had not synced `name`), #848 → #1226–#1229 (photogrammetric
  measurement; owner: do **not** overwrite Esri camera heading/pitch/roll, land GPX values as extra
  attributes), #875 → #1232/#1233 (embeddable 360 card, admin pinned view), #134 / #318 / #1410 /
  #1409 (export layouts, markers on PNG, capture sharpness), #320 (direction of travel; owner
  prefers no new OID attribute), #435 (cross-module asset deep-links), #507, #876 (spike: verify
  GlobalIDs and edit privileges).

### PM / fee estimate / CVS
- #1829 (owner: fee-estimate submodule "not working well in practice"; scope to be set with the
  owner; first step is rebuilding real estimate 26-100 beside the workbook), #950, #1301
  (estimated-vs-actual feedback for the calibration corpus, now six hand-extracted workbook
  cases), #1302 (sale database).

### GIS schema (asks made of the Portal layers; feeds task 0.5)
#1042 (attribute rule guaranteeing `lat`/`long` on points; 26-160 has none), #1026 (detector types
outgrow four fixed slots; related table like `xing_str_tbl`), #896 (`include` on `xing_str_tbl`),
#746 (retire `xing_str_equip1..4`), #747 (`has_switch_machine` on turnout/derail), #729 (widen
`sig_config`; long head configs truncate), #908 (case-size naming with embedded decimals), #1002.

## 2. Settled in threads, not in the ADRs

Nearly all of these are in `OWNER_RULINGS.md`, a second decision store beside the ADRs. ADR 0023
already carries the `oid`/OBJECTID amendment and ADR 0025 the UP-audit model; the rest was
checked by grep against the ADRs and not found.

**GIS and identity**
- GlobalID is the stable key; the Asset ID is display and write-back text (#1061, #904, #1496,
  #1888). SBIS originally stored no GlobalID; asset ids change early in a project. OBJECTID kept
  leaking through lookup and hand-off paths (#1104, #1129, #1510) though storage was GlobalID-first.
- Only the camera `oid` layers may key on OBJECTID (no GlobalID, static); declared on the dataset,
  not string-checked (#1894; ADR 0023 amendment).
- A dataset that had rows and now fetches zero refuses to land; an admin override covers one sync
  of one dataset and then expires (#1689, ruling 2026-09-11). A "large shrink" threshold was left
  open.
- The GIS freeze is one platform-wide hold, not a bulk per-project lock with a stored snapshot
  (#1687, ruling 2026-09-12). Releasing a Sync Lock deliberately does not re-enable Auto-Sync.
- No silent include-filtering: `include IS NULL` (nobody decided) differs from `0` (decided out),
  and excluded counts are shown (#1040, #827, #902).
- Scope is a project-level declaration over the whole dataset vocabulary (row absent = unset, no
  third enum value) and gates binding (#1669).
- A failed latest sync must not read as current because old rows remain (#1837).
- TIVS/CVS derivations once ran manually and drifted 19 days behind the platform copy (#1059).

**Costing boundary (SBIS ↔ TIVS)**
- Labor is a third designator on a catalog item, covering lump-sum and rate (#1045).
- A bungalow with no labor line values on material with labor zero, and says "no labor line"; an
  unpriced labor line still poisons the labor leg (OWNER_RULINGS 2026-09-25, #1957).
- Detector lump sums: coverage marked per line inside a bungalow, per site outside; a marked line
  sums as zero; the lump is an ordinary count-1 line; hand-netting was measured and rejected
  (#1990, 2026-09-28).
- The SBIS bungalow estimate is the engineers' pre-indirect material/labor estimate, with no tax,
  indirects or depreciation (#1958).
- Only the pre-indirect `(material, labor)` pair crosses to TIVS; price provenance is dropped
  there (#1434, open gap).
- Placement rule (#1054, worked on the crossing leg): interpretation moves down, policy stays up,
  identity has exactly one definition owned by the lowest layer that owns the data, with the raw
  value preserved. Four divergent `_collapse` normalisations existed (`crossing_source`, `tokens`,
  `asset_seam`, `rcn/sbis_prices`). In no ADR.
- Greenfield since 2026-07-27: no golden oracle for Schema 2 (#419 closed, #598); validation is
  sense-making with the Signal Engineers.
- Cost-table tabs are asset types with cost tables as sections inside (#985); complex trackwork
  stays its own process; a closed fee gate withholds the default, not the work (OWNER_RULINGS).
- Diamond / complex-trackwork condition weights: reference weights, configurable in settings
  (#1560, #1109).

**External evidence** (#1997, 2026-09-29; ADR 0025 accepted 2026-09-30): the audit never
overwrites the inventory; only `Complete`/`Partial` bungalows are compared; results are
provisional until a pairing is confirmed and states its relation; "not comparable" ≠ "SBIS
only"; decisions are recorded, never applied, and reopen when their basis moves.

**Platform and process**
- Document arc tabled (2026-09-18). Facts that survive: nothing holds or produces the appraisal
  report; no download is audited on any surface; the invoice is produced by QBO.
- Project `status` claims to gate the picker but gates nothing (#1301). A record sealed at project
  close must be small and hand-enterable so 2019 projects can be backfilled (owner 2026-08-23).
- A refused htmx request is surfaced once, in the kit, beside the control (#1690, option A).
  Refusals are HTTPExceptions with a sentence the user can act on.
- Only `RMI_DATABASE_URL` truly needs a restart on rotation; four bundle entries (QBO environment,
  QBO sync hour, QBO liability accounts, ArcGIS client id) are config, and each edit burns a
  Secrets Manager version (#1394).
- Test traps (#1236): `pg_session_scope` pins every session to one connection, so race tests on it
  prove nothing (use `own_scope`); the dev identity does not enforce CSRF; a word in a shipped CSS
  comment rides into every page head and trips substring tests; a "moves no number" proof must
  diff every published column, including blocked rows.
- Extraction PRs are byte-identical moves; behaviour bugs found in them become separate issues
  (#1505, #1515).
- Owner on speculative schema shape: "if it suddenly locks us into that direction, don't do it"
  (#1026). Footprint shading not pursued; SBIS Grid page retired; inventory-sheet batches cap at
  100.

## 3. Recurring bugs pointing at weak seams

1. **Identity: three keys in flight (GlobalID, OBJECTID, Asset ID).** #904, #1061, #1104, #1129,
   #1496/#1497, #1510, #1860, #1888, #1894. Cause: SBIS predates GIS; single-feature lookup was
   only offered by OBJECTID (#1496).
2. **Silent absence.** `include IS NULL` (#1040), blank asset_id dropped in reconcile (#822),
   complex trackwork and diamonds valuing nothing (#1558), out-of-domain values (#907), blank rail
   side (#1729), failed sync read as current (#1837), map swallowing query failures (#1515), htmx
   4xx/5xx showing nothing (#1690), unpriced structure blanking a percentage (#1572). Absent,
   undecided, excluded and failed are collapsed into one.
3. **The SBIS→TIVS seam.** #947, #1045, #1957, #1434, #952 (shell priced twice), #1214/#1218
   (blank bungalow rows), #792 (era-sensitive bindings), #1044, #1373. Themes: what crosses, who
   owns identity/normalisation, provenance lost at the crossing.
4. **Fixed-width slot containers.** `config_1..6`, `stand_type1..3`, `heater_type1..3`,
   `xing_str_equip1..4`, `surf_type1..6`, four detector slots (#946, #1099, #1026, #746, #410).
   Each forces cardinality rules (#897) and an arbitrary cap. `xing_str_tbl` is the accepted
   precedent for a related table.
5. **Units and labels drift from quantities.** #1213, #1373, #1493, #971.
6. **Staleness and emptiness of synced copies.** #1059, #1687, #1689, #1837.
7. **Generated UI built as strings in Python.** #1592 (rgba literals), #1927 (ids in URLs and
   selectors), #837 (f-string JS config blobs, ungated JS), #460 (a JS SyntaxError blanked every
   grid), #1505 (out-of-order async responses), six divergent page shells (#1575).
8. **Monoliths.** #842 (41 files over cap, one of 3,082 lines); #1138 (detail page reused as
   panel via a boolean flag).
9. **Test infrastructure.** #1943/#1951: about half of CI runs failed with asyncpg "attached to a
   different loop". The first diagnosis (an undisposed cached global `_engine`) was a real leak but
   not the cause; after fixing it 475 failures / 952 loop errors remained. Suspects left open:
   unset `asyncio_default_fixture_loop_scope`, mixed anyio and pytest-asyncio fixtures. Also #928
   (test schema built from models drifts from migrations), #1836.
10. **Deploy and secrets.** #1401, #1394, #1403/#12: hand-run deploys from one workstation,
    secrets snapshotted into env at boot, public DB endpoint.
11. **Decisions in two stores** (ADRs plus OWNER_RULINGS plus issue comments); ADR 0021 silent on
    the standing record after offboarding (#1301).

## 4. What this means for the rebuild

| # | Implication |
|---|---|
| 1 | **GlobalID is the only foreign key from day one**, SBIS included; Asset ID is an editable display attribute. Lookups by feature id only; OBJECTID is a locator. "Layer without GlobalID" is a per-dataset declaration (as #1894), not a code branch. |
| 2 | **Type the absent states**: present / undecided / excluded / failed / not-comparable(reason). Every count surface shows excluded and failed counts. Use for include, sync freshness, pricing gaps and audit comparison. |
| 3 | **Make each plugin↔plugin seam an explicit, versioned, typed contract** carrying price *with provenance* (date, completeness, source) so the consumer can snapshot it; identity/normalisation lives in the lowest owning layer (#1054). This is the MISSION "links offered and consumed" contract. |
| 4 | **Related tables, not numbered slots**, in the GIS schema proposal (0.5) and in cost identity. Keep reads behind a seam so the Portal need not change first (#1026). Propose attribute rules for `lat`/`long` (#1042) and `include` on child tables (#896). |
| 5 | **Write-back is a core-supported but late plugin**: queue (dataset, GUID, field, old, new, who, when), old-value guard at apply, pending overlay on reads (allowlist), dry-run, conflict-rate halt, size cap, per-field approval, inverse-change rollback. The MISSION decision holds; nothing in the issues argues against it. |
| 6 | **Snapshot what a valuation used**, including seam provenance and SBIS prices (#1434). Confirms the MISSION snapshot decision. Precedent: `fee_estimate_snapshot`; seal a small hand-enterable record at project close (#1301). |
| 7 | **Sync engine in core**: one Portal fetch per layer; module derivations run from the platform store on the platform cadence; refuse-empty guard with one-shot override; one platform-wide freeze; a failed latest run is visible (#1059, #1687, #1689, #1837). |
| 8 | **Kit before modules**: one shell and layout grammar; colours computed from tokens; helper-built, quoted URLs and selectors; one place that shows refused htmx requests; storage errors become actionable refusals; file-size cap enforced in CI from the start (#1575, #1592, #1690, #1927, #1935, #842). |
| 9 | **Test harness pinned early**: explicit event-loop and fixture loop scope, one connection strategy, test DB built from migrations (#928), documented `own_scope` vs `pg_session_scope`. The loop flake cost the current project a long stretch of coin-flip CI. |
| 10 | **Access model early**: project × module roles and capabilities (ADR 0017), narrow PATs (#1940), a client-identity story before CIV goes external (#261, #437, #1981). Server-side proxy for the browser map token (#1407) suits a plugin design; imagery behind signed URLs with file name as key (#1980). |
| 11 | **Ops belongs in the design**: config vs secret split and re-read on auth failure (#1394), tag-triggered deploy with approval (#1401), private DB (#1403), a tested restore (#1400), write-only immutable archive (#1422). Give each plugin an optional archive-exporter hook (capsule). |
| 12 | **Do not build what is tabled or undecided**: documents (#1298/#601/#1299), valuation year in PM (#950), strip maps (#131), BSIVS (#886). Fee estimator (#1829): keep the MISSION rule (configurable, overrides with justification, effort in days) and use #1301's estimated-vs-actual as the calibration path. |
| 13 | **One decision store**: ADRs, with rulings indexed and carrying a machine-readable status (ruled / tabled / open) linked from module manifests, so an LLM can tell them apart. |
| 14 | **Evidence-not-overwrite** (ADR 0025, #1997) generalises: third-party data (UP audit, GPX, client lists) lands in evidence tables with pairing and comparison, never in the inventory; a natural self-contained plugin. |

Open owner questions that gate design: store-vs-link test for documents (tabled); how a bungalow
finds its strip map (#131); anchor identity for CIV conversations (#1439); shrink-threshold
refusal (#1689); which rail quantity basis is right (#1373); class-grain vs per-component
crossing labor (#809); client identity (#261).
