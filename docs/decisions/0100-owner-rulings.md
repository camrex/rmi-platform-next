---
status: ruled
kind: ruling
date: 2026-09-29
refs: []
imported_from: rmi-platform/docs/planning/OWNER_RULINGS.md
imported_on: 2026-10-03
---
# Owner rulings

Decisions the owner has made that are too small to be an ADR and too settled to
be a plan. They live here because most of them have work attached that has not
been done yet, and **a ruling with nothing built against it belongs where the
next session will look**.

Split out of `ROADMAP.md` on 2026-08-20, when the roadmap became a generated
plan. The roadmap says what is next; this says what has already been decided, so
nobody re-litigates it. Where a ruling has a fuller home — an ADR, a design
paper, `COSTING_BOUNDARY_SBIS_TIVS.md` §0 — that document is authoritative and
this is the pointer.

Newest first.

## 2026-09-29 — UP's signal asset audit is evidence, reconciled against SBIS (#1997)

Union Pacific's Signal Asset Audit Inventory for 26-150 arrived this day. The
rulings below came in three rounds: in the owner's brief, in answer to the plan,
and after three independent reviews of the plan's first revision. The model is
[ADR 0025](../adr/0025-third-party-evidence-reconciles-against-the-inventory.md);
the mechanics and the waves are on #1997.

### What the audit is to SBIS

- **It is not a data replacement.** The audit never overwrites SBIS inventory.
  SBIS stays the source of record (ADR 0010).
- **SBIS says what matches and what does not**, and knows what the audit does and
  does not contain. A category the audit does not cover is "not comparable", not
  "SBIS only".
- **A decision changes no inventory.** Applying one is a separate step that needs
  the owner's separate approval.
- **Filling `Incomplete` bungalows from the audit is decided after the last wave.**
  It is the one use of the audit that writes inventory.
- **Another audit is possible.** A later workbook is a new import and names are
  railroad-neutral. No second reader is built until a second layout arrives.
- **All of it goes before the global catalog work**, which must carry the
  crosswalk across its re-cut of catalog rows.

### The surface

- **Its own surface, worked bungalow by bungalow**, and **separate from the GIS
  reconcile** (`/sbis/reconcile`).
- **Bungalows are named by asset id** everywhere on it.
- **Archived bungalows are shown on it, labelled, and never counted.** This is a
  stated exception to the 2026-09-16 ruling on #1160, for this surface only.
  Twelve of the sixteen out-of-scope bungalows that UP's cabins pair to are
  archived, and without them the surface cannot show why a cabin sits where it
  does. No tab count, progress figure or total includes them.
- **No valuation date is shown for now.** The dates band shows the audit, the 360
  capture and the SBIS inspection.

### Who does what

- **Pairing and deciding are project admin only.** Everyone with SBIS access
  reads. ADR 0017 §4 classes reconciliation as editor work; this sits at the admin
  tier by the owner's answer. **The role is enough**: no new facet and no ADR 0017
  capability.
- **The owner maintains the crosswalk.** The Signal Engineers read it.

### Pairing a cabin to a bungalow

- **The platform proposes and the owner confirms.** An unconfirmed pairing is
  compared, marked provisional. A decision can be recorded only once the pairing
  is confirmed or overridden.
- **Pairings may be confirmed in bulk only where nothing disagrees.** Each records
  that it was confirmed in bulk and on what criteria.
- **A cabin that is another structure at the same site is a second kind of
  pairing**, shown side by side and not scored. Nagle Ave is the case: UP's cabin
  is the new house, beside the crossing bungalow SBIS holds.
- **A cabin that is a structure SBIS does not have is recorded, and nothing is
  created.** The bungalow arrives through GIS. This is the owner's choice for this
  surface: ADR 0023 still permits an unlinked bungalow, and the create form is
  unchanged.

### The comparison

- **Only `Complete` and `Partial` bungalows are compared**, the same line as the
  2026-09-16 ruling on #1555. `Incomplete`, `No As-Built` and out-of-scope
  bungalows are not compared, and UP's list is still shown.
- **UP's `In Service-Normal` and `In Service-Standby` units count.** `Spare` and
  `Out of Service` are shown and not counted.

### The workbook

- **The file is kept in platform storage, and cannot be downloaded.** This covers
  the audit workbook and UP's April cabin registry. **It is not a ruling on
  #1298**, which stays tabled, and must not be cited as one.

**The waves** are re-cut from the first plan: the crosswalk comes before pairing,
because pairing counts contents in it. Seven waves, #1998 to #2004.

**ADR 0025 was accepted on 2026-09-30** ("ADR 0025 APPROVED"), the day after it was
filed as Proposed. The pointers in ADRs 0010, 0016 and 0023 lost their caveat with it.

## 2026-09-28 — detector lump sums: marked per line inside, per site outside (#1990)

The detector supplier priced two site types as lump sums, by track count:
HBD/HWD/DED sites (one figure for bungalow components, one for track components)
and AEI sites (one figure for both). DED-only and weather-only sites stay priced
by component, and they hold the same components.

- **Coverage is per bungalow and per site, not per item.** The cost row's
  `in_lump_sum` (#1470) covers an item everywhere on the project, and a ticked
  row that carries a price is still summed — so it cannot say "covered here,
  priced there". It stays as it is; these marks are beside it.
- **Inside the bungalow: a lump-sum mark on the equipment line.** The engineers
  mark the covered components in each lump bungalow. A marked line sums as zero
  **whatever its price**.
- **Outside: one mark per detector site**, ticked on the bungalow page's External
  Equipment card. The lump covers every exterior component at the site, so the
  whole site is covered at once. It crosses the seam, and TIVS sums that site's
  rows as zero and publishes `priced_by = SBIS lump sum`.
- **The mark names the bungalow that covers the site, and is honoured only while
  that bungalow can carry the money.** It must still be related to the site, not
  archived, linked to GIS, and valued on its contents. Otherwise the site prices
  by component again, rather than valuing at zero with its money nowhere. A
  second bungalow related to the same site never stands in.
- **The lump itself is an ordinary count-1 line on the bungalow** (the 2026-09-16
  ruling, unchanged). No fourth designator and no catalog marker.
- **Accepted for now: the exterior money sits in the bungalow.** It depreciates on
  `bglw_cond` rather than the detector rows' `equip_cond`, and the detector site
  reads $0. Interior and exterior depreciate alike for these sites today. Whether
  the track lump should land on the site is **#1990**, to assess later.
- **Netting the lump by hand was measured and not taken.** Across the six
  HBD/HWD/DED sites on 26-150 it needs three exterior and four interior
  deductions — close to one hand-computed lump per site.
- **Kept small on purpose.** The global catalog work may re-cut how costs divide
  between SBIS and TIVS.

## 2026-09-26 — batteries are cells (#124), and a priced-but-unused catalog row still blocks

- **#124, batteries as cells.** A battery catalog row is one **cell** — amp-hours
  plus a `voltage` (**2 V on every row**, the 18-cell Absolite included). The cell
  count moves to the instance, which carries `cells`, a `strung` flag (these
  cells are one series string) and an optional free-text note where a UP battery
  code (`B06`, `B16`) goes when a drawing printed one — nothing is derived from
  it. Two entry modes on the equipment grid, **By string** (each string with its
  cell count) and **Cell count** (cells of an amp-hour, structure not read); they
  mix in one bungalow. String voltage, the `14C (28V)` grouping label and the
  price (per cell × cells) all derive. Migration rulings: a multi-cell row held
  n times becomes **n strung rows** (the structure was known); a single-cell row
  held n times becomes **one unstrung row of n cells**; the owner fixed the one
  price that broke the per-cell rule (12-cell 472 AH at the 475 AH rate) in
  production, so per-cell prices derive from the rows. The **"Ah total" line
  retires** on the bungalow page and the inventory sheet, and the battery totals
  report drops its amp-hour column (amp-hours do not add in series). Sequenced
  **before the global catalog epic** (`rmi-sbis-extract` `CATALOG_ENTRY_SPEC.md`
  § 6.10 assumes it); slices #1967–#1970 release together as one MINOR. The
  design note and the rulings table are on #124.
- **#1965, catalog delete.** A cost row that Generate created and nobody priced
  is scaffolding: the delete sweeps it. A row that is priced, lump-summed,
  completed or locked **blocks**, as before. Warn-and-allow for priced-but-unused
  rows was raised and **not taken**: the global catalog re-cuts cost rows, so the
  policy would be decided twice.

## 2026-09-25 — the bungalow estimate (#1958) and the labor leg under the flip (#1957)

- **#1957: a bungalow with no labor line values on material.** Once an internal
  line stops poisoning the labor leg (its labor is MASKED at the seam, #680, not
  missing — a line contributes only to the legs its designator prices in), a
  bungalow with no labor line sums labor to **zero** and values on material. The
  SBIS estimate page and project grid say **"no labor line"** on every such
  bungalow, so nothing is silent; an UNPRICED labor line still poisons labor.
  Chosen over the named-gap reading (nothing values until every bungalow has a
  labor line): labor per bungalow is a capability the engineers may use, not a
  gate. The sum lives SBIS-side (`sbis.estimate`), one summer for the estimate
  and the valuation.
- **#1958, the estimate surface — three more.** A partial estimate shows a
  **muted "priced so far"** subtotal beside its gaps, never labelled as the
  estimate (the asset page's grammar). An xlsx export of the bungalow estimates
  grid is a **later slice**, when the engineers ask. **"Complete" means every
  line priced or accounted for** (the owner's words: "every line priced") —
  derived from the gaps, so a lump-summed line (accounted for, #1470) does not
  hold it back; the cost rows' Complete mark is the engineers' own bookkeeping
  and is not part of the estimate.

## 2026-09-18 — the document arc is TABLED, and the backup grant is closed

- **#1298, #601 and #1299 are all tabled by the owner.** The decision paper's five
  questions were put; the owner answered Q2 (**hold** the appraisal report rather
  than point at it) and then tabled the rest: *"I am working on something on the
  side that may alter how we handle this."* So the store-vs-link **test is not
  settled**, #601 does not ship, and #1299 does not go ahead. Q2's answer stands as
  the owner's intent but **cannot be acted on until the test is** — holding the
  report is a conclusion the eligibility rule has to reach, not a substitute for it.
  Do not re-put these questions unprompted; the side work lands first.
- **What the paper measured, which survives the tabling.** Three contradictions of
  #1298's own premise, all measured: `pm.Document`'s categories split
  client-supplied from internal, **not** produced from received, which removes the
  paper's only empirical support for the producer test; SBIS's as-built plans are
  **received** material the platform has stored for a year and nobody thinks it
  wrong; and the invoice is produced by **QBO**, yet the invoice design stores it by
  the attribute test in prose. Two facts worth keeping regardless: **nothing in the
  platform holds or produces the appraisal report**, and **no download is audited
  anywhere, on any surface**.
- **#1916 is fixed, live.** ADR 0021 said the app needs only `s3:PutObject` on
  `backups/` — no delete. The policy never implemented it, and there was **no
  template/reality drift**: the live `rmi-platform-app` user carried the template
  verbatim, so both were wrong and nothing was out of sync to notice. An explicit
  `Deny` on `s3:DeleteObject` + `s3:DeleteObjectVersion` now covers
  `rmi-platform/backups/*` **and** `rmi-platform/*/backups/*` (a set
  `RMI_STORAGE_S3_PREFIX` would otherwise step around the one prohibition that
  exists to be unbypassable; the prefix is unset in production). Applied to the live
  user 2026-09-17 and re-simulated: the same key went **allowed → explicitDeny**,
  while the nightly `PutObject` and the PM shelf's purge still succeed.
- **v1.57.0 browser-checked and correct.** 26-150's nine CIV bookmarks list in
  milepost order. "No MP" on 25-340 / 25-320 / 26-170 is the expected reading, not a
  bug — those projects' `oid` datasets are bound but have never had a sync succeed.
- **#1440 does not wait on the owner's cutover pass — it waits on the Signal
  Engineers.** Measured on production: 26-150 is the only project with any
  `sbis.catalog_cost` rows (461), and **not one carries a price** — zero
  `unit_cost`, zero `labor_unit_cost`, none completed, locked, dated or sourced.
  Flipping `sbis_prices.signal_structure` today would take all **345** SG assets to
  a MISSING gap (799 component lines, every one missing both halves). Component
  pricing has not started. Re-measure those counts before picking it up again; the
  flip is a one-line settings change the moment they are non-zero.

## 2026-09-17 (late) — the GIS join key, v1.57.0, and #1298 gets a paper

- **The GIS-corrections deliverable is renamed to `asset_id`, and the ADRs are
  amended.** `/sbis/reconcile-corrections.csv` and its `.xlsx` twin still headed
  the asset id `bglw_id` after #1473 renamed it in the JSON API and #1910 in the
  export workbook. That name belonged to the column #1472 dropped, so the
  deliverable was the last place it survived. One name everywhere wins over a
  preserved join: **ADR 0008** (which documented "the GIS team joins the CSV on
  `bglw_id`") and **ADR 0007** (which describes the CSV as the deliverable) are
  amended rather than quietly contradicted, and the release note tells GIS staff
  to repoint their join. **No deprecation window and no duplicated column** —
  the same posture as #1910, and for the same reason: two names for one value is
  how the old one survives another year.

- **v1.57.0 is cut now, as a MINOR.** #1884 (bookmarks in milepost order), #1889
  (migration `0042` deleting the inert `civ/oid` module rows) and #1910 ship
  together. MINOR rather than PATCH because of the new ordering behaviour plus
  **two breaking read contracts** in one release — the workbook header and the
  corrections join key. `0042` is order-indifferent, so this release may migrate
  before or after deploying.

- **#1298 gets a decision paper before it is ruled.** The document-repository
  question — what the platform stores versus what it references — is not being
  answered off the cuff, because #601 and several later asks all hang on it.
  A paper goes on the issue: what file surfaces exist today (measured), #1298's
  produced-vs-received test stated fairly, every named artifact sorted by it,
  what storing produced artifacts costs under ADR 0021's durability obligations,
  the strongest case for leaving ADR 0014 alone, and the handful of questions
  that actually need a yes. **#601 stays held until that ruling.**

## 2026-09-17 (after v1.56.0) — four answers on what comes next

- **#1910: the xlsx headers become `asset_id`, with no deprecation window.** The same
  ruling as #1473 gave the JSON API, for the same reason: one name for the asset id.
  The importer accepts only the new name, `docs/powerquery/*.pq` changes with it, and
  the release note carrying it says so FIRST, because a workbook reading `bglw_id` by
  name stops working.
- **#1884: bookmarks key their frame on OBJECTID**, like #1488's `?oid=` deep link, and
  read the milepost from the synced `oid` row matched by it. This supersedes the
  2026-09-16 "keyed on GlobalID, never OBJECTID" for bookmarks only: no OID layer
  publishes a GlobalID, and the 2026-09-17 ruling accepts an OBJECTID for these static
  catalogs. Existing bookmarks keep working untouched, and if the layers ever gain
  GlobalIDs, bookmarks move with everything else.
- **#1889 rides the next release** rather than getting one of its own. The rollback
  floor passed v1.54.0 when v1.56.0 migrated, which was all it was waiting for; the
  rows it deletes are inert.
- **#601 waits on #1298.** The equipment-document shelf is not built until the owner has
  ruled what the platform is the system of record FOR (produced versus received). The
  design that keeps the attachment point open is on #601.

## 2026-09-17 (night) — the asset id after the column drop, and how it ships

Asked while #1472 (drop `bglw_id` / `external_id`) and #1419 were in review.

- **An unlinked row shows "not linked" on a page and BLANK in exports.** The xlsx
  export and the PAT JSON feed carry null; only the rendered page carries the words.
  A sentinel string in an id column is something every Power Query consumer would
  have to filter out, and #1471 already shipped the blank (`str | None`) shape.
- **GIS owns the asset id, and correcting a typo from SBIS is gone.** The reconcile
  page's "apply" on the Asset ID field is retired with the column: a rename is simply
  the new name once the sync lands it, and a typo is fixed in GIS. This is the point
  of the GlobalID work — one holder of the id, no second copy to disagree with it.
- **#1472 ships alone, deploying BEFORE it migrates** — asked and answered twice. The
  first answer was "#1908 in a patch now, #1909 alone later"; both then landed on main
  together (my sequencing error), and the owner chose **one v1.56.0, deploy then
  migrate** over two off-line tags or a revert. So v1.56.0 carries the card change,
  the batch cap and the drop, and the rollback floor moves past v1.55.0 with it.
- **Next up is #1884** (bookmarks by milepost from the synced `oid` rows), ahead of
  #452 and #1440.

## 2026-09-17 (evening) — inventory-sheet batches cap at 100

- **#32's batch cap is 100 bungalows** (was 50). Measured first: the owner's first
  production batch rendered 21 bungalows (one sheet each) in 32 s, about 1.5 s a
  sheet, so 100 bungalows is about 155 s against the worker's 300 s job limit. It goes
  no higher until the worker's memory while merging a large PDF has been measured.

## 2026-09-17 — `oid` syncs on demand only, once a landing is batched

- **#1420 measured it.** A full `oid` landing against the real layers, into a local
  database: 25-320, 106,524 frames, 711 MB peak memory, 17.8 s, 102 MB of rows; 26-150,
  51,110 frames, 402 MB, 9.6 s, 54 MB. The sync holds the whole layer in memory, and
  production's 1 GB node is shared by api, worker, Redis and Alloy.
- **The owner's answer: on-demand only, after batching.** `oid` never joins the
  nightly sweep, because camera metadata changes only when a capture run is
  published, and that is when to press Sync. The on-demand hold stays until #1899
  lands a dataset page by page, so memory is bounded by the page, not the layer.
  #1419 and #1884 wait on #1899.

## 2026-09-17 — an OID frame may be named by its OBJECTID

- **No production OID layer publishes a GlobalID.** The v1.54.0 pre-release check
  (read with the app token) found no `globalIdField` and no GlobalID-typed field on
  `a25320_360_oid`, `a25340_360_oid`, `a26150_360_oid` or `a26170_360_oid_2`. Each
  is Query-only and carries `objectid` and `join_key`. The owner's answer: "for
  now OBJECTIDs are okay in referencing the OIDs. Since these are essentially
  static catalogs that don't change they should be stable". The owner will look
  into adding GlobalIDs to them.
- **This is the OID catalog's exception, not a change to "OBJECTID never".** Every
  other dataset still keys on its GlobalID, and where an OID layer gains one, the
  GlobalID wins.
- **What it changed before v1.54.0:**
  - The 360 card's "Open in full CIV" link (#1488) falls back to `?oid=`.
    Without that it was never drawn on any live layer.
  - The Data page's "Sync GIS data" also holds `oid` back. This narrows the
    night ruling below, which kept on-demand sync; every such sync could only be
    refused.
- **What it leaves open:** letting the dataset sync key `oid` on its OBJECTID,
  which #1419 (cameras from synced rows) and #1884 (bookmarks sorted by milepost)
  need.

## 2026-09-16 (night) — the oid sweep hold, and what #1471 leaves for #1472

- **#1418: `oid` is held out of the nightly GIS sweep.** Once `oid` is a project
  dataset it would sync on every CIV project with Auto-Sync on, and the camera
  layers are large (about 106k features on 25-320) with an unmeasured cost. The
  scheduled sweep skips it, while "Sync GIS data" on a project's Data page still
  syncs it. Built with #1418 (PR #1891). #1420 measures the cost and removes the
  hold.
- **#1471: the 8 placeholder bungalows on 26-150 are deleted.** They are the only
  bungalows with no GlobalID, all archived and Excluded, and their ids are blank,
  `???` or `BG-01-000000`. The notes read as duplicates or replaced plans, and
  they have no equipment, units, relations, annotations or conversations
  (measured on production 2026-09-16). A data migration removes exactly those
  rows and refuses if any has gained a child row. Measured the same day: every
  linked bungalow's stored `bglw_id` equals its GIS `asset_id` (1,218 of 1,218).
- **#1471: a GIS-field acknowledgement needs a GlobalID.** One without is to be
  refused; today's writer still accepts one, and #1471 builds the refusal. All
  425 acks on production carry one.
- **#1888: signal assets key on GlobalID, not `external_id`.** It blocks
  #1472. The registry's only uniqueness, and TIVS's price join, move to
  `(project, type, GlobalID)` before #1472 drops the column.

## 2026-09-16 (evening) — bookmark mileposts, CIV's panel, provenance, strip maps

Asked while working the Todo column; each names what it unblocks or retires.

- **#322: bookmarks sort by milepost read from the SYNCED `oid` dataset, keyed on
  GlobalID, never OBJECTID.** Not a milepost copied onto the bookmark at save
  time, and not a browser-side ArcGIS query. Two things follow: #1418 (promote
  `oid` to a platform project dataset) comes first, and a bookmark stops keying
  its frame by OBJECTID, which is reassigned on republish, the same reason
  #1488's "Open in full CIV" link names the frame by GlobalID. Built as #1884;
  folders and search shipped separately (PR #1883).
- **#1431: CIV keeps TIVS's panel.** CIV owns no arrangement: the pano
  click-through embeds the TIVS `panel` surface as shipped in #1131, and the
  TIVS `page`/`panel` surfaces are the one panel definition. The `civ:pano` card
  slot (#1432) registers on those surfaces. #1433 (a CIV-owned arrangement) is
  declined. This settles #506's recorded "CIV divergence" in favour of one panel:
  CIV shows what TIVS's map panel shows, value cards included.
- **#1425 and #1426 close as moot.** Per-field provenance existed to make the
  bulk "Adopt all" safe, and "Adopt all" was retired (#1738), and #1427 was already
  closed as not planned on the same grounds. With them, #462's last slices are gone.
- **#131 (Signal Strip Maps): not now.** The maps are in S3 under
  `SIGNAL_STRIP`; how a bungalow finds its map (milepost range or the GIS
  `sig_strip_map` attribute) stays undecided until the issue is picked up.

## 2026-09-16 (afternoon) — the owner-decision queue, answered in one pass

Asked once the easy queue was empty; each answer names the issue that builds it.

- **#1160: archived bungalows leave project-wide counts, everywhere.** Summary totals
  and completion %, the export workbook and the Power Query/token API all use the same
  active-bungalow scope (`sbis.scope.active_bungalows`) as the views v1.52.0 fixed.
  Power Query row counts change, so the release note says so. **The default map hides
  archived bungalows' GIS features unless "Show excluded" is checked.** Today that box
  only restores the web map's own `include = 0` filter, and the features route ignores it,
  so this is new behaviour: unchecked, the route also sends the archived bungalows' asset
  ids for the map to exclude.
- **#558: TIVS money rounds to the cent inside the calculation, now.** The cascade and
  stored rows round, not only the served frames. Totals shift by pennies and old and
  new snapshots will not diff to the cent. It lands without waiting for #598's final
  parity review, which accounts for cent-level differences.
- **#777: admins can soft-delete conversation posts.** Super admin and project admin.
  The body is blanked behind a "removed by an admin" tombstone, the act is audited, and
  the post's mentions drop out of the Inbox. The thread keeps its shape. This amends
  ADR 0019's non-goal ("corrections are replies"). **The role is enough** (`can_admin`):
  no ADR 0017 capability, because a soft, audited tombstone on project data is in-project
  administration rather than a dangerous verb.
- **#1469: no fourth designator. A lump sum is a count-1 catalog item in the designator
  its money belongs to**: `internal` for material only, `external` for material and
  labour, `labor` for labour only. So material tax stays correct, and nothing new is
  built beyond saying so. #1470's "accounted for" points at this.
- **#1555: the pre-phase trust signal reads bungalow Status, in three answers.**
  - Complete and Partial are **trusted**: missing parts warn.
  - Incomplete is **muted**: still a to-do.
  - No As-Built and Excluded **raise no missing-part findings at all**.
  - A blank Status falls back to today's surveyed-equipment proxy.
  - A recorded phase still overrides the inference, **except** that No As-Built stays
    silent under any phase. ADR 0024 §5.4 is amended for that exception.
- **#1466: a cost workbook sheet keeps ONE header row**, the column union, with a
  styled section row naming each cost table and shading on identity cells a table
  does not use. The header contract is unchanged, and the importer skips section rows
  rather than reading them as cost rows. The grid keeps the union with
  section labels, as v1.52.0 shipped. No labelled per-table identity. #1467 builds it.
- **#1499: an admin decides which sync history to delete.** Not an automatic
  retention window: a platform admin chooses the runs to remove, across every
  sync-run table (platform, TIVS, CVS), and a run's gap rows go with it and never
  otherwise. A run cannot be deleted while anything still depends on it: a source's
  latest succeeded run, or any run a landing, derivation or valuation snapshot
  references. Every deletion is audited. **platform_admin is enough**: no ADR 0017
  capability. This amends ADR 0016's "never pruned" and ADR 0021's
  rejection of pruning provenance: pruning becomes a deliberate, audited admin act
  rather than something app code does on its own.
- **#1480: already ruled** (#1140, below): hand-maintaining CIV's slot list is fine
  because a test catches drift. Closed on that ruling.

## 2026-09-16 — the two `bglw_id` contract names, image backfill, the rotation reminder

- **#1473: both contract names become `asset_id`, outright.** The SBIS JSON API's
  bungalow, equipment and unit feeds emit `asset_id` where they emitted `bglw_id`,
  with no deprecation window carrying both. The Units list's `sort=bglw_id` URL key
  becomes `sort=asset_id` with no alias, so an old bookmarked sort URL falls back to
  the default order. Power Query workbooks that read `bglw_id` by name must change,
  so the release note carrying this says so first. `docs/powerquery/Grid.pq` is
  updated in the same change.
- **#1421: no backfill beyond the rollback floor.** Save v1.50.0 (the rollback floor)
  and v1.51.0. Every earlier release not already in `images/` (only v1.19.0, v1.26.0
  and v1.27.0 are) is **accepted as lost**, not rebuilt from its tag, since a rebuild
  is not the image that ran.
- **#1387: the rotation reminder is a scheduled GitHub workflow**, not a standup line,
  so it fires on days nobody runs standup.

## 2026-09-15 — four leftovers that held nearly-finished epics open

Asked while clearing open parents with one sub-issue left.

- **#1725: the dashboard panels are proven.** Retire `/tivs/overview` and
  `/tivs/inventory-summary` and their renderers. The summary's Power Query endpoint stays,
  as ruled 2026-09-14, so `tivs.inventory_summary` stays with it.
- **#1430: section names go in the exhibit's per-process frames too**, not only in the
  "Value by section" table. A real PDF proves nothing clips.
- **#1464: build the header tooltips.** A shaped TIVS grid column names the GIS field it
  came from for the link the project is bound to, with a written fallback for merged and
  derived columns.
- **#1288: the fee estimate submodule is revisited as a whole**, in #1829, which supersedes
  the one-off rebuild of 26-100. #1288 and #1253 are closed.

## 2026-09-15 — the project configuration index: who sees what

Ruled on the three questions [CONFIG_INDEX_DESIGN.md](CONFIG_INDEX_DESIGN.md) §4 left
for #1540. All three recommendations were accepted:

- **Show everything, and gate the links.** Every configurable surface is listed. A line
  the viewer cannot operate names who can (*needs platform admin*) instead of linking.
  Filtering to reachable surfaces would leave "where do I configure X" unanswered for
  exactly the reader who lacks the tier.
- **Anyone with access to the project opens the index.** It shows names and locations,
  not values. The stored-settings panel shows values, so it needs project admin.
- **Orphaned keys are listed and deletable** by a platform admin, audited. The five
  `sync.derive_from_synced` rows in `tivs.tivs_setting` are the first to go.

## 2026-09-14 — where #898's include toggle lands, and what readiness judges

Ruled while slicing #898 (sub-issues #1798–#1802), where
[INCLUDE_AT_VALUATION_DESIGN.md](INCLUDE_AT_VALUATION_DESIGN.md), written before the
dashboard existed, disagreed with the dashboard as built:

- **The toggle goes on the per-process detail grids, and the dashboard links to them.**
  The paper put it "on the inventory" (§4.4) and on the dashboard (§9, and item 6 of
  2026-08-20 below). The dashboard as built lists no rows, so it links instead: family
  rows and panel sections open the grid (#1801). Summary frames with Total rows get no
  toggle, because a count is `include = 1` always.
- **Readiness stays on valued records.** The paper's §6 (walk every landed row, classify
  every rule) is superseded by item 4 of 2026-08-20: ADR 0024 decision 6 is extended case
  by case, so a rule that needs excluded rows argues for itself on its own issue.
- **The toggle is remembered in the browser only**, per process. (§8 Q2)
- **A deliberate `0` and a blank are marked apart**: *Excluded*, and *Include not
  stated*. (§8 Q4)

## 2026-09-14 — the dashboard panels close out; a map image, and an endpoint that keeps every asset

Ruled while finishing #1723 and planning what follows it:

- **Rail & OTM readiness counts side records** (#1742). The grain is the one its total
  and grid already count in. Segmented processes key readiness marks by record, not by
  asset id.
- **#1723 closes without the value-total panel.** §5 gave it one job: to resolve a
  *mixed* total to each family's snapshot. The page reads one snapshot, so *mixed*
  cannot occur, and the identity band already names that snapshot, its date and its
  basis. The design's §5.5 records this.
- **#1724's map is a static image of a Portal web map**, not a live map and not the
  bound layer's MapServer export.
  - **How it renders:** server-side, through the org's Export Web Map task, cached per
    project, never in first paint.
  - **How it is bound:** per project, like the other web-map bindings, so each project
    names its own map. No item id is hard-coded.
  - **The ADR:** 0016's 2026-09-11 amendment, which named only generated documents as
    callers, is widened in the same PR.
- **#1725 keeps `/api/v1/tivs/inv-summary`**, and it must carry every asset the project
  holds. The Power Query templates stay on it.
  - **The audit found three types missing:** turnout complexes, diamonds and
    generators. #1772 adds them, with a guard test for any process added later.
  - **Retiring the old pages is still gated** on the owner saying the panels are
    proven.
- **v1.49.2 shipped as a PATCH**, the owner's call over MINOR, carrying the panels and
  #1742.
- **The project map lives on the project home, not the TIVS dashboard** (#1780). Ruled the
  same day #1779 put it on the dashboard, before it shipped: the home has room, and a
  project map is not one module's. The TIVS dashboard carries no map.
  - **It is framed from the platform's synced rows**, so it works whatever modules a
    project runs. TIVS's milepost text appears beside it only where TIVS is enabled.
  - **The release waits for the move**, so production never gets a TIVS-only map slot to
    migrate bindings out of.
- **Slab (direct-fixation) track** (#1787). 26-150 now carries 20 included segments with
  `surface_type = SLB_TRK` and `tie_type = NONE`.
  - **Ballast:** both BALLAST and SLB_TRK are allowed. SLB_TRK is not valued: 0 tons,
    priced $0.
  - **Ties:** `tie_type NONE` values at $0, material and labor.
  - **Rail & OTM:** on direct fixation, plates, spikes and anchors are 0. A new
    `direct_affix` OTM table prices fasteners each, as material, with one price and no key.
    The count is one per rail side per spacing interval, and the spacing is a project
    setting, provisional until settled (default 24 in).
  - **What counts as direct fixation: both must agree.** Only SLB_TRK with NONE. Either
    value alone is a GIS inconsistency, flagged and blocking until GIS is fixed.

## 2026-09-13 (late) — complex trackwork stays its own process; its slots follow its counts

Ruled while checking complex trackwork readiness on 26-150:

- **Numbered slots are expected only up to the record's count.** Frog slot N is
  checked only where `frog_cnt >= N`, and the point, stand and heater slots
  likewise against `point_cnt`, `stand_cnt` and `heater_cnt`. This is the
  crossing-surface rule (`num_tracks`, #334). Slot 1 is always checked.
  - **Why:** every slot was asked of every record. All 17 TO_MPFs on 26-150
    carry one frog and were warned for frogs 2 and 3.
  - **What still warns:** the 4 DSLIPs that claim four points but record two.
- **The turnout and complex trackwork merge is tabled.** Complex trackwork is
  rare, and most projects only ever carry NML turnouts. 26-150 is the
  exception, so the two stay separate processes.

## 2026-09-13 — a fourth bar for the page, and the archived choice is the session's

Ruled on the SBIS bungalow detail (#1748) and TIVS asset prev/next (#1749):

- **Bar 4 is the page's.** Record navigation and actions that a long page's reader
  used to scroll back up for sit in a fourth sticky chrome bar, kit-owned: a page
  declares it, and a page that declares nothing gets no bar. The bungalow detail
  is the first user; TIVS asset detail is the second.
- **"Include archived" is remembered for the browser session**, not carried in the
  URL. `?archived=1` (#1747) held only along the links that threaded it, and
  ⚙ Main systems and back reset it.
- **TIVS asset prev/next stays within the asset's section**, in milepost order,
  then asset id; an asset with no milepost goes last. Stepping through the grid's
  current filter was declined for now: the grid has no URL state to carry it.

## 2026-09-13 — readiness lives on the readiness page, in tabs

Ruled while reviewing readiness after v1.48.0 (#1745):

- **Tabs by module.** The project Readiness page opens on an **Overview** tab, the
  summary table that sat on project Home, then has one tab per module.
- **Severity order.** A module reads blocking, then warning, then info, with info
  collapsed by default. A record still carries every problem on it together
  (ADR 0024 §4.3) and is listed under its worst severity.
- **Off project Home.** Home no longer loads readiness. Even loaded lazily, every
  module walking the project made it slow.
- **Asset subtabs in TIVS.** The TIVS tab has one subtab per asset family (and one
  for project-wide findings), so the page rarely needs scrolling.
- **`/tivs/readiness` is not decided yet.** Whether the TIVS readiness page is
  retired is decided after this ships and has been read on 26-150. It still holds
  the readiness overrides, the asset-scope card and per-family ready counts.

## 2026-09-13 — a track segment must not leave a rail side blank

Asked on #1727 (dashboard slice 1) whether any track segment leaves a rail side
blank: *"We shouldn't, and we certainly want to know if we do have any of these."*
Rail & OTM values a segment with one side blank as single rail, at half its track
feet, and drops a segment with both sides blank from rail valuation. Readiness sees
neither, because a dropped side produces no record.

TIVS's catalog therefore gains `tivs.rail.sides_stated` (#1729): authored, locked, over
`track_cl_inv`. It flags an included segment whose rail weight, grade and year are all
blank on either side, which is exactly the side Rail & OTM drops, and names the
segments. Production held none on 2026-09-13.

The severity is the issue's default proposal, not part of the ruling: informational
during survey, a warning while costing, and blocking at valuation and delivered through
the lock floor. The owner can revisit it.

## 2026-09-13 — the SBIS Grid page is retired

Ruled while working SBIS readiness: *"Given that SBIS has grown so much, it just
doesn't make sense to keep, as it is laggy, and no longer serves a function that is
usable."* (#1734)

The page (`/sbis/grid`) and its CSV (`/sbis/grid.csv`) are removed, along with the nav
entry, the SBIS home card and the Export page's CSV button. **The bungalow × item pivot
is not lost**: it remains the workbook's **Grid** sheet (`/sbis/export.xlsx`), whose
columns are a consumer contract, together with the shared queries behind it.

## 2026-09-13 — SBIS function fields, the HVAC mirror, and the reconcile buttons

Ruled while working SBIS readiness, after a bungalow's GIS HVAC changed from No to Yes and
SBIS kept No. On live production, three 26-150 bungalows sat that way: BG-01-000107,
BG-02-000087 and BG-02-000126. The full reasoning is on #892.

1. **The function fields move into the Bungalow Comparison table** (Equipment, Class,
   Comm/Ants, Sort, HVAC). The separate "differs from GIS" card, "Adopt GIS" and **"Adopt
   all" are retired**. Nothing records whether a value was typed in SBIS on purpose, so a
   bulk adopt reverts every such edit in one click. (#892)
2. **HVAC mirrors from GIS on every sync**, as PTC does. It is a GIS observation: a
   visible A/C. (#1731)
3. **The "Refresh function fields" button is removed.** Its fill-blanks work, which never
   overwrites, runs after every sync instead, including crossing track counts from the
   crossings layer. (#1732)
4. **SBIS's "Sync now" stays**, because it is convenient, but it says it syncs
   **bungalows only**. Data → Sync GIS data remains the platform-wide sync. (#1731)

## 2026-09-13 — crossing equipment and surfaces are separate dashboard rows

Ruled on #1728 (dashboard slice 3): *"for crossings, we should keep crossing
surface and crossing equipment separate."*

This overrides the TIVS dashboard design's §10.2, which had put `xing_equipment`
and `xing_surface` on one "Crossings" row because both read every crossing. They
are now two families, **Crossing Equipment** and **Crossing Surfaces**. Each has its
own records, quantity, costs and money. On 26-150 that means surfaces read as valued
and equipment reads *not valued*, rather than one row reading partial. As with ties,
ballast and rail over `track_cl_inv`, both rows count the same crossings, and the
quantity column offers no total across them.

## 2026-09-12 — an empty-landing grant does not outlive the state it was reviewed against

Ruled on #1697, split out of #1693's review and widened the same day.

**Record the reviewed state on the grant and refuse if it moved.** The grant
carries the binding identity (service name, service type and layer id — never a
URL, per ADR 0016) and the set of enabled modules that read the dataset. A sync
that takes a grant whose state has moved does **not** apply it: the run is
refused as an empty landing, and the refusal names what changed.

Chosen over revoking grants on the transitions and over an age cap alone,
because it is the only option that tells the admin *why* their override did
not apply. A grant that silently disappears when a binding is repointed would
be the one shape of this feature that teaches people not to trust it.

**The legitimate-rebind case has the same answer**: refuse, name both states,
and let the admin accept again against the layer as it is now. The refused
grant is spent and keeps the reason it was not applied, so the Data page offers
acceptance again rather than sitting on a grant that can never apply.

It covers all three transitions the issue names. As built (v1.47.7):

- **Binding repointed** — compared at consume time.
- **Consuming module disabled and re-enabled** — the module set reads the same
  afterwards, so comparison alone cannot see it. Module enablement and binding
  set/clear leave a note on any armed grant (never spending it), and a noted
  grant refuses, quoting the note.
- **Age** — a grant older than **7 days** does not apply. The value is an
  implementation choice, not part of the ruling: the sweep runs daily and a
  grant is spent by the next sync, so a week-old grant means nothing has synced
  the dataset since it was given.

## 2026-09-12 — the GIS freeze is one platform-wide hold, not a bulk lock

Ruled on #1687, after the 2026-09-11 Enterprise outage was handled by locking
six projects one at a time and restoring them in twelve acts.

**Design B: a platform-wide GIS hold, consulted beside each project's lock.**
One setting; while it is on, every gate treats every project as locked. No
per-project value is ever written, so "restore to the previous state" holds **by
construction** — nothing to snapshot, no drift if a project is changed by hand
during the hold, no Auto-Sync re-arm, and no ADR 0023 §3 amendment. A project
created during the hold is covered too.

**Design A (bulk lock + stored snapshot) is not being built.** It would have
needed a ruling on the §3 tension — restoring Auto-Sync on release *is* a re-arm,
which §3 calls "its own visible act" — plus a reconciliation path for projects
deliberately changed mid-hold, to reach an outcome B gets for nothing.

**The prep work is the first slice and stands on its own merits.** The lock is
read directly in five places today rather than through `get_sync_controls`.
Routing them through one gate is worth doing whether or not the hold follows;
the hold then becomes part of that one answer, which also lets a refusal say
*why* it is locked — project lock or platform hold, with the reason and who set
it.

## 2026-09-12 — two monitoring gaps are worth filing

Ruled after the post-outage review found the 2026-09-11 Enterprise outage was
invisible in monitoring for its full 70 minutes.

Both filed: **#1698** (the sweep records success even when every dataset failed,
and no alert exists) and **#1699** (nothing reports GIS reachability). Neither is
covered by #1402, which is about metric plumbing rather than sync semantics.

The constraint recorded with #1699 matters more than the feature: a GIS
reachability signal must **not** sit on `/healthz`, because the Lightsail public
endpoint health-checks that path — a liveness probe that fails during a third
party's outage would pull our own container and turn a degraded app into no app.

## 2026-09-12 — #985 stays open until its slices land

Its three slices (#1465–#1467) remain sub-issues rather than being detached to
stand alone as #1061's were, so the wave stays visible as one thing on the board.

Recorded because the close that prompted the question was an accident, not a
decision. #1694's body described the issue as *"a board decision rather than a
file f&#8203;ix"* with the issue number immediately after — and GitHub parsed
that as a closing keyword at merge, one second later. The sentence said the
change was *not* made here; the negation is irrelevant to the parser, and so is
the fact that the trigger word was an ordinary English noun rather than a verb
about closing.

**The quoted phrase above carries a zero-width space on purpose.** This exact
mistake has now happened four times, and twice the *second* close came from a
follow-up that quoted the phrase to explain the first (#1061, 2026-08-31). A
Markdown file does not autoclose anything by itself, but a tracked file holding
the live phrase is a loaded gun for whoever next quotes it into a commit message
or a PR body. Before pushing either, run:

```bash
grep -inE "(clos|fix|resolv)[a-z]*[[:space:]]*:?[[:space:]]*#[0-9]+" <file>
```

That check is the only thing that catches the fourth case, because nothing about
the sentence's meaning gives it away.

## 2026-09-11 — a dataset that had rows refuses to land empty

Ruled during the Enterprise GIS upgrade window (#1689), while the count guard
(#1691) was being written.

**A dataset whose last succeeded run landed rows refuses to land none.** The
count guard compares a fetch against the layer's own count, which catches a
fetch the layer contradicts. It cannot see the case where query and count
*agree* on zero — indistinguishable, from the platform's side, from a layer
someone genuinely emptied, and exactly what a half-up server returns when its
services are up before their data store is. Landing it re-derives the TIVS typed
inventory and the CVS subject segments from nothing. So the run fails before the
delete, the landed rows stay, and the hooks skip.

Two cases are not refused at all, because there is nothing to protect: a
never-synced dataset, and one whose last succeeded run already landed zero.

**The override is ruled but shipping separately.** A platform admin accepts an
empty layer for one sync of one dataset, from that dataset's row on the project's
Data page, reason required, audited as `admin.gis.accept_empty`; the next sync
spends it and the guard re-arms by construction, because a flag would sit armed
after the sync it was meant for. That half is held back on the owner's ruling
2026-09-12: the guard was stable from its first review round while every
subsequent finding landed in the override, so the safety half ships first and
the override follows as its own change. Until then a genuinely emptied layer
refuses every sync with its rows intact.

**Not ruled, and left open deliberately:** whether a *drastic shrink* (say more
than half the rows gone) should be refused the same way. Genuine large deletions
happen during inventory clean-up, so a threshold is a judgement call; zero is the
only case with an unambiguous answer.

## 2026-09-04 — the UI arc: fluid pages, three bars, Pico plus a token layer

Four rulings on #1575 during the slice-1 review (PR #1582), each recorded on the
issue that owns the work.

**Every page is fluid.** *"I use monitors from laptop to 57 inch, I prefer to
size the window to what I need, versus the page be set."* No page caps its own
width: the reading/wide page kind, PM's 60 rem and 96 rem caps, CVS's 78 rem cap
and the `wide=` flags are gone; `main` is always `.container-fluid`. Built in the
slice-1 PR (#1582), open at the time of writing.

**Navigation is three bars — app, project, module.** Bar 1 is the app (brand,
Inbox, Ask / report, Projects, Admin, Sign out). Bar 2 is the project (logos,
code, Home · Data · Readiness, and the modules the reader holds, current one
marked). Bar 3 is the module's own surfaces. Nothing repeats across bars; a bar
with nothing to say is absent, not empty; TIVS keeps its sidebar for the asset
tree and its project-level links move to bar 3; marking is derived from the
request path. Proposal and confirmation on #434; slice 4 builds to it.

**Styling is option B: Pico stays, a kit token layer and vocabulary go on top,
no build step.** Chosen from the four options in
`docs/planning/UI_STYLING_OPTIONS.md` (also posted inline on #1575). The owner's
framing: ADR 0004 was early and *"now we need a professional, properly styled
consistent application"*. B answers it without a framework change: one tokens
file overriding Pico's variables plus the kit's own tokens, the component
vocabulary drawn from them across slices 2–5, and an `/admin/style` page that
shows every component in one place for review. If B still reads as "Pico with
a coat of paint" after slice 5, option C (own base on a reset) is the next step
and the tokens carry over. Slice 2 (#1578) is scoped to this.

**Brand inputs are sampled, not specified.** The RMI blue is taken from the
logo (#034b65; the wordmark charcoal is #12181e), the system font stack stays,
and dark mode must keep working. Posted on #1578.

**Reading remotely.** The owner often cannot read repo files until they are on
main. A paper that needs a decision is posted inline on the issue that owns it;
the repo copy stays the record.

## 2026-08-31 — the Data Management page is the platform's, and it acts

Three rulings on #1156, plus one that unblocks #1140.

**It is a platform surface, linked from PM — not a PM page.** The owner framed
it as "within PM" and the issue argued otherwise; the argument held. It is built
at project grain as `/p/{code}/data`, owned by the platform, with PM's workspace
linking to it prominently. The aggregation stays registry-driven, so it reports
on modules it does not import — the trick aggregate readiness already uses.
Housing it in PM would have made PM the one module that reaches into TIVS and
CVS, which is the module-to-module coupling ADR 0002 exists to prevent.
Navigation and ownership are separable and this separates them.

**project_admin ACTS; platform_admin still WIRES.** Running a sync, viewing all
state, clearing orphaned rows, setting asset scope and reading readiness move to
`project_admin` — those are the daily acts of whoever runs the engagement, and
making them leave the project to perform them is the complaint that opened the
issue. **Engineers are not in this** — the Signal Engineers hold viewer and
editor grants, and syncing is an admin act at every tier: *"Engineers have no
control over sync. It is the admins job to sync."* `project_admin` here means
the person running the engagement, not everyone inside the project.
Changing the ArcGIS folder, creating or repointing a dataset binding, and
engaging the sync lock stay `platform_admin`. The distinction is not seniority:
a wrong binding is SILENT — the valuation still computes, on the wrong data —
while a badly timed sync is visible and re-runnable.

**A line dataset in the pano (#1140 slice 2): nearest point for fences, nothing
for the centerline.** `slide_fences` is a discrete structure worth spotting, so
it gets a marker at the nearest point on the line. `track_centerline` becomes
bindable and shows no marker: it runs under every frame, so a marker for it is
either always present and useless, or arbitrary. The point half of #1140 already
shipped; this settles the half that was held.

## 2026-08-30 — a stale reconcile page still acts

**#1061's mutation routes fall back to the asset-id column when GIS no longer
answers to the id they were posted.** A page loaded before a rename posts the
old asset id; strict GIS resolution would refuse it. It does not, because
nothing downstream is keyed on that segment — the feature, the acks and the
comparison all go through the GlobalID — so only the label that started the
request was stale. Refusing was weighed and would have turned a page a few
minutes old into a 404.

Self-extinguishing: slice 5 drops the column, and strict resolution becomes the
only possible behaviour at the point where there is no second key to disagree.
Fuller record, including the archive guard a rename had been silently switching
off, in
[GLOBALID_RELATIONS_DESIGN.md](GLOBALID_RELATIONS_DESIGN.md)'s 2026-08-30
addendum.

## 2026-08-30 — the create form stops requiring an Asset ID

**A bungalow may be created without one.** The form was the strictest thing in
the stack and the only one that could not say why: `sbis.bungalow.bglw_id` is
nullable, [ADR 0023](../adr/0023-gis-ingestion-contract.md) makes an unlinked
record a *supported state* rather than an error, and six production rows on
26-150 hold NULL there today. Leaving it blank now creates the bungalow unlinked
and it links on a later sync — the same answer `globalid_for_asset_id` already
gives for an id GIS has not caught up with.

**The blank stores NULL, never `""`.** `uq_bungalow_project_bglw` is
`UNIQUE (project_id, bglw_id)`, so an empty string would allow exactly one
unlinked bungalow per project and refuse every one after it — the option would
have worked once and then looked broken. Pinned against the real constraint in
`test_sbis_pg_create_unlinked.py`.

## 2026-08-22 — a closed fee gate withholds the default, not the work

**A gate that fails must never stop an estimator billing time.** Client-provided
mapping still sometimes takes some, so the `Range(0, 0)` a closed gate produces
means *the module is not proposing hours*, never *you may not enter any*. Raised
against [SPEC](pm/fee-estimate/SPEC.md) §5.5 while reviewing slice 2 (#1255),
where the derivation read *"not applicable"* and so described a prohibition the
engine does not actually impose.

The engine already behaved correctly — §5.6 writes a zero line for every
targeted resource exactly so an override has somewhere to live, and an override
on a gated line is kept. What changed is the wording (*no default hours — …*)
and a test that pins the behaviour rather than leaving it implied.

**The open half is the grid (#1259).** §5.2 records that in the workbook a
non-zero value was what revealed a row. If the grid inherits that and hides zero
rows, the gate becomes the prohibition this ruling says it is not — so a gated
zero line has to stay reachable, on the grid or through quick-add.

## 2026-08-20 — eight answered in one pass

1. **~~#1195~~ — SPLIT the key.** Built and closed the same day, and ~~#1157~~
   closed with it. `sbis.bungalow.size_shell` keeps the valuation demand (*no
   shell line for this class/size*, and *size not set*, which blocks the
   derive); a new **`sbis.bungalow.shell_stale`** carries the contradiction
   (*stored shell disagrees with what the fields derive*). Only `size_shell` is
   suppressed on an excluded bungalow. The two want different actions from a
   reader, which is the usual sign they are two rules. This is what held
   ~~#1157~~ open.

2. **#1156 — the platform owns it, at `/p/{code}/data`.** Not a PM module page:
   `platform_core` imports nothing from `modules/`, and the readiness aggregate
   already solves this shape with a registry the composition root wires. PM's
   workspace links to it prominently.

3. **#1156 — the access split is real.** `project_admin` runs syncs, views
   state, clears orphans and sets scope. **Dataset binding and the sync lock stay
   at `platform_admin`** — a wrong binding silently changes what a valuation
   stands on, and the lock is [ADR 0023](../adr/0023-gis-ingestion-contract.md)
   §3's freeze over delivered work.

4. **[ADR 0024](../adr/0024-validation-engine-and-project-phase.md) decision 6 —
   extended CASE BY CASE, on issues.** The ADR stays as written; no blanket
   inversion. A rule that needs to see rows the process filtered out argues for
   itself with a measurement, the way ~~#1157~~'s blank-`include` rule did. Every
   inversion therefore arrives with evidence rather than as a rule nobody can
   check.

5. **~~#1161~~ slice 3 — plain English, not SQL.** Built the same day. SBIS's and
   CVS's rules are authored over OUR database, so a pasteable layer query does
   not exist for them and one would invite a paste that cannot run. Each states
   its condition in a sentence an engineer reads — *"PTC flag is No but PTC
   components are recorded"* — beside the TIVS rules that show real SQL. The
   surface's value is understanding why a rule fired; only TIVS's half of that
   happens to be executable.

6. **#898 — design NOW, build after the seam.** The design is written:
   [INCLUDE_AT_VALUATION_DESIGN.md](INCLUDE_AT_VALUATION_DESIGN.md), with the
   owner's narrowing — counts stay `include = 1` **always**, the inventory
   defaults to included-only with a toggle. ≈1,027 excluded rows across the three
   active projects are invisible today; on 26-160 the complex turnouts are 33
   included against 54 excluded. It also depends on **#1202**, the
   inventory-dashboard rebuild, because the toggle and the counts land on that
   surface and it is about to be replaced. The build stays sequenced behind #947.

7. **#985 — ASSET TYPE tabs, with the cost tables as sections inside.** 17 tabs,
   not 22 — an engineer navigates by the thing they are pricing — but a fan-out
   tab (`rail_otm`'s seven, `slide_fence`'s two) carries a visible section header
   per cost table rather than one flat sheet. Answers both objections: navigation
   and opacity.

8. **#723 cutover completion — still open, and the owner's own pass**: clear the
   queue, base specs, prices, xing rebind + re-inject, flips. BRPST pricing tiers
   still need the Signal Engineers' word (token guide TBD).

## 2026-08-20 — an act, not a plan

**Re-engage 25-320's Sync Lock.** It has been off with auto-sync on since
2026-08-19, so [ADR 0023](../adr/0023-gis-ingestion-contract.md) §3's freeze over
that delivered valuation is currently disengaged. Engaging it is
`/admin/gis/{project}` → the Sync Lock switch, which takes a reason and audits it
as `admin.gis.sync_lock`; the same UPDATE disables Auto-Sync, so the CHECK holds
throughout. **The reason text is the record of this decision**, which is why it
wants a session rather than a row write.

## 2026-08-09 — deferred so the mechanism can land first

How diamonds and generators are differentiated, and how detectors are identified
(#992). Both get easier once assemblies price in one place. As of v1.22.0 all
three families are *in the inventory* while those decisions wait — which is the
point of the split.

**Valuation year (#950) is out of the cost-identity work and tabled.** It was
briefly sequenced in on the assumption that SBIS would need the same basis to
price against; **SBIS is not a consumer**. SBIS records an `estimate_date` per
priced row and the valuation-year logic stays TIVS-side, so the seam carries
costs without either side agreeing a year. The real consumers are TIVS and CVS,
which each keep their own copy.

## 2026-09-01 — the snapshot footprint is not pursued

**#318's footprint shading is dropped; #1411 closed.** Neither shape is built —
no FOV indicator composited onto the exported still, and no companion map image.

It was the one item #318's body hedged as *"if feasible"*. The defect people
actually reported was that the same view exported from a small window and a
maximized one produced different-sized PNGs, and the v1.31.0 capture viewfinder
fixed exactly that. Nothing has asked for a footprint on an exhibit since, so an
unrequested "if feasible" item was carrying a standing decision prompt on the
board instead of being answered.

The map dock keeps its cone and inverse coverage shading — this was only ever
about what leaves the app as a file. #318's remaining export work is #1409
(measure capture sharpness) and #1410 (markers compositing), which was always
the larger and more-requested half.

Settles a downstream question too: **#874 attaches the pano still and nothing
else**, because there is no companion image to decide about.

## 2026-09-02 — four decisions that were the whole queue head

The board had five owner calls standing between finished work and anything
queued. Four were answered in one pass; the fifth (#1399) was sent back for
facts first, which is recorded below.

### #1501 — the inline-JS sweep stops at 77%

**Closed at 1,884 → 440 lines, 22 → 14 islands.** None of #1501's four stated
reasons still applies at the remaining sizes: no file is near the 500-line cap
because of its island, a 15-line island is not "edited blind", a diff that small
reads fine as a Python string, and caching an 8-line asset is noise. All
fourteen stay syntax-gated inline by #460, so nothing is unprotected.

The three that were a **design** question rather than a size one —
`BROWSER_TOKEN_JS`, `PDF_PANEL_JS`, and the `SBIS_APP_JS` concatenated onto one
— became **#1529**, which must answer *where a platform-level asset is served
from* before anything moves.

### #1156 slice 5 — sequenced, not retired in one act

The order is **#1205 → #1487 → #1486**: land the unified sync surface, repoint
every Sync link at `/p/{code}/data`, and remove the per-module triggers **last**.
Nothing is taken away before its replacement is in front of users, which is what
makes this a sequence rather than a removal.

### #1061 — closed at the end of build scope; slice 5 stands on its own

Slices 1–4 shipped and the display half finished by surface. Holding the issue
open for slice 5 made a finished arc read as in-progress work. The drop is
irreversible and buys nothing but tidiness, so it is scheduled on its own merits
as **#1471** (retire the last `bglw_id` / `external_id` statement sites),
**#1472** (drop the columns) and **#1473** (decide the two `bglw_id` names that
outlive the column). Those three already existed as #1061's sub-issues; they are
now detached so they do not dangle under a closed parent.

They also carry the thing most easily lost: the reconcile **comparison** reads
`bglw_id` legitimately, because that is exactly where the stored value versus the
GIS value is the point. The drop must not sweep it out.

*(I first filed a fresh issue for this without checking #1061 already had three.
`scripts/roadmap.py`'s dangling-wave guard caught the duplicate within minutes;
it is closed as not-planned.)*

### #904 and #1140 — closed

**#904**: both root causes shipped, zero by-OBJECTID lookups remain, verified
against production's served bytes. The surviving OBJECTID path is a deliberate
fallback so a pre-deploy browser tab keeps resolving — the designed end state,
not residual work.

**#1140**: hand-maintaining CIV's slot list is **fine**. A test catches the
drift, so deriving it is tidiness rather than correctness; #1480 holds the
derivation option if it is ever wanted.

### #1399 — stay on `small`, budget ~2,500, and say that it moves

Answered the same day, once the numbers were in. **Keep Lightsail power `small`
and rule the budget at ~2,500 rendered rows — noting explicitly that this is
subject to change if the container size is increased.**

What the measurement showed: `small` is 1.0 GB per node shared by api + worker +
redis + alloy, running at 274–367 MB, so the api gets ~885 MB and about 3,000
rows — 2,500 is roughly a 20% margin, and the figure holds on the shared node
rather than being eroded by it. There is no operational pressure to upsize
(27–36% memory, 2.9% mean CPU); the only standing argument for `medium` is
halving the CPU peaks, which is a responsiveness question to decide on its own
merits.

The arithmetic that settled it: snapshot #14 is 9,275 records, so a per-record
report over it needs ~9,275 rows. `small` misses by 3.7x, `medium` (+$300/yr)
**still** misses by 1.3x, `large` (+$780/yr) fits only until the records grow.
Buying RAM does not buy the report, so the design rule is needed at any size.

Because the budget moves with the node, the number lives in exactly one place —
`RENDER_ROW_BUDGET` in `platform_core/documents/render.py` — with ADR 0012
carrying the constraint and the three design questions. #1490 and #1492 are the
implementation.

Corrected on the way: `docs/DEPLOYMENT.md` said `micro` was 0.5 vCPU and implied
`small` had more RAM. Measured against the AWS API, `micro` and `small` both have
**1.0 GB** and `small` buys double the vCPU — so the recorded reason for moving to
`small` (fitting the alloy sidecar) cannot have been about memory.

## 2026-09-02 — the sync-page shape (#1484), and what it means for run history

Four shapes were offered on #1484. The sequence the owner chose — **#1205 → #1487 → #1486** —
described in the question as *"land the unified surface first, repoint
every link, then remove the triggers last, so nothing is taken away before its
replacement is in front of users"* — is **shape 2: read-only run history, the
triggers dropped.** Not shape 1.

That distinction is the whole ruling, so it is worth stating why rather than
just which. `/p/{code}/data` today shows **freshness and coverage only**. It
carries no `TivsSyncRun`/`CvsSyncRun` history, no per-source gaps table and no
per-source state table — `render_data_page` composes `_freshness`, `_coverage`
and `_elsewhere` and never touches a sync run. Retiring `/tivs/sync` and
`/cvs/sync` outright would therefore delete three blocks with nowhere to go,
which is exactly the "taken away before its replacement is in front of users"
the chosen sequence rules out.

So:

- **#1487 thins.** Every nav entry, in-page link and README pointer resolves to
  `/p/{code}/data`, which becomes the one answer to *"where do I sync"*. The
  module pages keep run history, the latest run's gaps and (TIVS) the
  per-source state table, and link out for freshness. An old bookmark gets a
  thinned 200, never a 404.
- **#1486 then drops the triggers**, once the links already point elsewhere.
- **Run history stays on the module pages until it has a home.** Moving it is
  #1156's business — what a Data Management page should *show* — not this
  consolidation's.
- Binding and the sync lock stay `platform_admin` on `/admin/gis`, unchanged
  from the 2026-08-31 ruling: a wrong binding silently changes what a valuation
  stands on.

Shape 4's defect is already fixed — **#1483** gated `POST /cvs/sync/run` at
`project_admin`, closing the gap where an editor could trigger a CVS sync while
getting no button on the platform page the ruling governs. (Not #1485, which is
a duplicate of it and closed as not-planned — Copilot caught the misattribution,
and it matters: it would send the next reader to a not-planned issue looking for
a fix that shipped somewhere else.)

## 2026-09-02 (evening) — three rulings, and where sections are actually defined

### #1482 — an included record must state a section

The owner's words: *"require section to not be null if include = 1. Plain and
simple. If an assignment only has 1 section, then all sections are 1."*

This is a stronger answer than the three shapes #1482 offered, because it
removes the obstacle rather than working around it. The difficulty was never the
14 typed tables — `RulePredicate.source` exists for exactly that. It was that the
RCN counter gates on `uses_sections`, a PROJECT-level, data-derived question
("does any source here carry a section at all") that no per-table `WHERE` can
carry; a predicate without it would over-select on a project using no sections,
which is the failure that decided SBIS's case. The ruling says no such project
should exist, so the gate is not encoded — it is retired as a premise.

TIVS's catalog therefore gains `tivs.section.stated`: authored, locked, presence
taxonomy, one pasteable predicate per section-carrying source,
`(include = 1 AND section IS NULL)`.

**What `locked` costs, said out loud**, because the bite map alone gives the
wrong answer: a locked rule is BLOCKING at valuation and delivered whatever its
map says (ADR 0024 §4.4). So this refuses a valuation sign-off over a sectionless
record — informational during survey, warning while costing, blocking at the end.
That is the right end state for a ruling phrased as *require*: a valuation signed
off over such a record is signed off over one that priced at the project default
rate and is missing from every section rollup, at the last moment it is fixable.

Nothing blocks today, measured 2026-09-02: 26-160 is the only project at
valuation and has zero sectionless records; 25-320 holds the single one and has
no phase set, so it resolves stage-blind to `info`. What the floor does is stop
the next one arriving unnoticed.

**Verified against production before authoring, and again after.** Of 6,966
included records across the three live projects, exactly **one** is sectionless
(25-320, `generator_inv_pt`) — the same record #1481's separation left standing.
All fourteen predicates, pasted verbatim into prod, select that one record and
nothing else: no over-selection, no under-selection.

**Consequence not taken here:** `load_uses_sections` still gates the RCN counter,
and under this ruling that gate is describing a state that should not exist. It
never fires today (every live project carries sections), so retiring it is a
follow-up rather than a silent behaviour change inside a catalog addition.

### #1529 — the shared-kit trio stays inline

`BROWSER_TOKEN_JS`, `PDF_PANEL_JS` and `SBIS_APP_JS` are not extracted. All three
are syntax-gated by #460, none is near the line cap, and the concatenation
(`APP_JS = PDF_PANEL_JS + SBIS_APP_JS`) exists so a module loads ONE script.
The question the issue was filed to force — where a platform-level asset is
served from — is answered by not needing one yet; `platform_core.web.assets`
already has the machinery when a real consumer wants it.

### #1077 — the observation window is over

Proceed. The preconditions are met, #1059 closed on them, and the window has run
long enough. Its body's carve-out remains STALE and must be read with that in
mind: zero of the 14 TIVS sources lack a dataset since #1107, so "dataset-named
sources" now means the live path entirely — a larger and more irreversible act
than the issue's text describes.

### Where project sections are defined, since it was hard to find

The registry exists and the owner built it: `platform.project_section`
(`platform_core/sections/`), stewarded by PM, rendered as the **"Sections"** card
on **`/pm/workspace`**, with `POST /pm/workspace/section` and
`/pm/workspace/section/delete` behind it (#468).

Measured 2026-09-02: **26-160 is the only project with sections named** (six of
them). Every other project has zero rows — the codes render bare, which is the
"labels are additive" design working as intended, and also why the surface is
easy to forget.

## 2026-09-03 — #1558, the two rulings that let diamonds and complex trackwork ship

Asked while building, because the framework had no answer and the handoff said
to ask rather than assume.

### The diamond's four condition legs blend at stand-in weights, configurable

The question: a diamond prices as ONE assembled unit, so there are no component
cost shares to weight its frog / guard rail / timber / ballast legs by — the way
the turnout blends. Equal weights, named reference weights, or wait for the
engineers?

The owner's words: *"Reference weights, use what you have, but make them
configurable in settings, if possible."*

What "what you have" resolved to: the NML turnout's default panel row mapped
leg for leg (frog keeps 0.30, guard rail takes the point's 0.20, timber keeps
0.25, ballast takes the rail's 0.25). Borrowed, not measured, and the process
says so with a `provisional` note the way complex trackwork does. Configurable
became a per-project setting with its own card on the depreciation config page
(`depreciation.diamond_weights`, four fields, blank = default, must sum to
one). The engineers' weights are #1560, the diamond twin of #1109.

### Both processes select depreciation by density class

The owner chose *"Yes, both by dens_class"* over one wildcard row each and over
splitting the two. Same shape as the turnout: three assignment rows per project
per process, no wildcard fallback expected, and a record on a density with no
row skips naming that density. `dens_class` therefore became required on
`diamond_inv_pt` (#1550's rule: required exactly where the pipeline reads it) —
17 of 17 included diamonds already carried it.

### What the measurement changed about the issue itself

The 0 valued / 0 skipped in #1558's body was real but not silence: both were
hard exceptions recorded in the count row's `error` column, and on the plain
RCN run before the snapshot `turnout_complex` had already processed 55 records
and skipped all 55 loudly. 26-160 carries no complex trackwork and no diamonds
at all, so its "no prepared records" rows were truthful. The full table is on
the issue.

## 2026-09-10 — the asset scope is the platform's, and it follows the bindings

Asked for as *"TIVS 'asset scope' toggles should move to the data page"*, then
clarified while the first cut was under review: *"While certainly this is in
TIVS and its scope has been associated with TIVS, it is meant for all. It
generally follows the bound assets."*

What that settled: the asset scope (#899) is not a TIVS setting rendered on a
platform page but a **platform fact about the project's bound datasets** —
scope = the bound datasets minus the ones deliberately excluded — stored on
the binding itself (`project_gis_dataset.in_scope`, bound ⇒ in scope until
someone says otherwise) with the scope lock beside the sync lock on the
project row. Every module reads it through `platform_core.arcgis.scope`;
TIVS projects it per source through the dataset each source declares, and
its own `scope.assets` / `scope.locked` settings retired (production had
stored them on zero projects, so nothing migrated). The surface is an **In
scope** column on the Data page's Datasets table.

What the #899 quadrants became under that model: *bound but out of scope* is
a deliberate declaration (a notice on TIVS readiness naming the Data page,
not a mis-binding warning); *in scope with zero rows landed* stays the notice
a human reads; *declared in scope but unbound* cannot be said — scope follows
the bindings — so "this module wants a layer nobody bound" stays the admin GIS
page's unbound-slot list. Taken as the default; the owner can ask for that
loud case back on the Data page if it is missed.

## Deliberately not queued

**#598's findings triage.** The parity gate is long gone, so nothing is blocked
on it — it is a final review before legacy retires, for when there is time.

## Open owner actions (not issues)

Data work sitting with the owner, found 2026-08-07, all pre-costing on 26-150:

- 22 turnouts in section 05 need `has_heater` set.
- 12 need a heater type — 8 at count 1, and 4 claiming three heaters while
  naming none.
- 8 assets across 26-150 / 26-160 are dropped from valuation by an *unset*
  `include` rather than a decision.
- 3 GIS-included bungalows marked Excluded in SBIS want `include=0` in GIS.
