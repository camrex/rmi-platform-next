---
status: ruled
kind: architecture
date: 2026-09-30
refs: []
source_status: "Accepted (2026-09-30 — proposed 2026-09-29, accepted by the owner the next day) · **Extends**: [ADR 0010](0010-bungalow-inventory-sbis-source-of-record.md)"
imported_from: rmi-platform/docs/adr/0025-third-party-evidence-reconciles-against-the-inventory.md
imported_on: 2026-10-03
---
# 0025 — Third-party evidence reconciles against the inventory, and changes it only by a separate approved act

**Status**: Accepted (2026-09-30 — proposed 2026-09-29, accepted by the owner the next day) · **Extends**: [ADR 0010](0010-bungalow-inventory-sbis-source-of-record.md)
(SBIS stays the source of record) · **Adds to**: [ADR 0016](0016-gis-data-access-posture.md) §3
(a third class of data, by origin) · **Follows**: [ADR 0023](0023-gis-ingestion-contract.md) §5
(a link is an attribute of the record, not its identity) · **Informed by**: the owner's
rulings of 2026-09-29 on #1997, and three independent reviews of that plan's first revision.

The owner's rulings it rests on are recorded in
[OWNER_RULINGS.md](../planning/OWNER_RULINGS.md) under 2026-09-29. Waves 0 and 1 of #1997
were built while it was Proposed; nothing in them contradicts it.

## Context

Union Pacific's Signal Asset Audit Inventory for 26-150 arrived on 2026-09-29. It is the
railroad's own field-tagged registry: every tagged unit, under the chassis it sits in, under
the cabin that houses it. It is the first source the platform will hold that is neither GIS
nor RMI's own survey.

Its value is that it is independent. SBIS's finished bungalows were read off house diagrams
and part counts; the audit was entered by someone standing in front of the unit. Where the
two agree, each corroborates the other. Where they differ, both can be right: a drawing
shows what was designed, the audit shows what is there on the day it was taken.

Two ways of using it were available and both are wrong. Loading it into the inventory would
make SBIS a copy of a source it cannot answer for. Ignoring what the source does not cover
would turn its silence into disagreement: the audit lists two plain relays against about
3,800 in SBIS's Chicago bungalows, because UP does not tag relays, not because they are
absent.

The platform has no decision that says what such a source is, where it lives, or what it may
do. ADR 0016 §3 names two classes of data by origin and this is neither.

## Decision

### 1. Third-party evidence is a third class of data, by origin

ADR 0016 §3 names GIS-origin data (synced from the Portal, shared by default) and
platform-origin data (exists only here, module-owned). **Third-party evidence** is a
statement received from outside, about the same assets, made by someone else as of a date.

It is held by the module whose inventory it speaks to, in that module's schema, **beside**
the inventory and never inside it. It is keyed by the import that brought it, so a later
statement is a new import and the earlier one stays.

### 2. It never writes the inventory

Nothing that values, exports or crosses a seam reads third-party evidence. For SBIS that is
the ADR 0010 seam, the estimate, the exports, the reports, the inventory sheets and the
analytical API. This is enforced by a test that fails the build on the import, not by
convention: a documented rule the build does not run is a wish.

### 3. Evidence is paired to a record as an attribute, never as an identity

A UP cabin is paired to an SBIS bungalow. The pairing points at the bungalow's own
surrogate id, so it rides along when the bungalow is relinked (ADR 0023 §5), and is
reviewed again when that happens.

**The platform proposes; a person confirms.** A proposal never becomes a fact by being
computed. A comparison may be shown under a proposal, marked provisional. A decision may
not be recorded under one.

A pairing states its **relation**: the same structure, or another structure at the same
site. An equipment record is not a building.

### 4. Comparison has three outcomes, and both sides' silence is protected

A line **agrees**, **conflicts**, or is **not comparable**. "Not comparable" always carries
its reason.

| whose silence | what protects it |
|---|---|
| the source's | each category states its coverage: what the source records, records only sometimes, does not record, or records and is deliberately not compared |
| the source's, in one place | a person may record that the source did not record this category here |
| the inventory's | a record the module does not yet trust is not compared; the source's list is shown as information |

Which records a module trusts is the module's to state, and it states it by name. For SBIS
it is the line the owner ruled on #1555 and again on #1997: a bungalow whose status is
`Complete` or `Partial` **is compared**; one that is `Incomplete`, `No As-Built` or out of
scope is not. "Not finished" is not the test, because a `Partial` bungalow is not finished
and is compared.

The comparison is computed when it is read and never stored, as SBIS's rollups are not.

### 5. A decision is a record; changing the inventory is a separate, approved act

A decision on a conflict records who, when, why, and the state it was made against. It
changes nothing in the inventory. When what it rested on moves, the decision returns for
review and says what moved.

Applying a decision to the inventory is a separate act that needs the owner's separate
approval. No mechanism for it is decided here.

### 6. The vocabulary that maps the source's names to ours is global

The crosswalk from the source's model names to catalog items is global, like the catalog
it points at, and per issuer. An edit to it moves the comparison on every project that
holds evidence from that issuer, including one already delivered. That is accepted: the
comparison is not a valuation input (§2), and a decision records the vocabulary it was made
under (§5).

### 7. What is kept, and where it is backed up

The parsed evidence is in the database and so in the nightly dump. It may carry client
data, such as serial numbers, and the backups therefore do too.

Whether the received file itself is kept is decided per source. For the UP audit and UP's
cabin registry the owner ruled that it is, in platform storage, with no download. That is
an answer for those two files. It is **not** a ruling on what the platform stores and what
it references (#1298), which the owner has tabled.

A stored file is in the versioned bucket and not in the dump, so a re-parse on a restored
database without the bucket must fail loudly.

## Consequences

- SBIS gains a package that holds evidence, a pairing, a crosswalk and decisions, and a
  surface of its own. It is separate from the GIS reconcile by the owner's ruling.
- ADR 0010 is unchanged in substance: SBIS is still the single inventory source of record.
  This ADR says what may sit beside it and what that may not do. The inventory's own
  pages may **show** the evidence beside the record — the bungalow page carries the
  pairing and each line's standing against the audit, with a link to where it is worked
  (owner ask, 2026-09-30) — and may not act on it: every pairing, decision and
  disposition is recorded on the audit's own surface. The allowlist test that keeps the
  package beside the inventory names that page as a reader for this reason.
- The global catalog work must carry the crosswalk across its re-cut of catalog rows, and
  reopens the decisions that rest on the rows it re-cuts.
- The project archive of [ADR 0021](0021-backup-restore-and-data-durability.md) §3 must be
  complete and readable in isolation, and the comparison is computed, not stored. So a
  capsule carries the project's evidence, pairings and decisions **and the crosswalk as it
  stood at the archive**, for every issuer the project holds evidence from. The crosswalk
  is global and so is not a project-keyed row; it is reference data the project's rows are
  read through, as the equipment catalog is for its inventory. A capsule without it could
  not rebuild a comparison, and one read through the crosswalk of the restore day could
  rebuild a different one. The capsule exporter (#1423) owns the mechanism.
- A second source, from UP later or from another railroad, is a new import and, if its
  layout differs, a new reader. Nothing else is built for generality until one arrives.
- The mechanics, the waves and the owner's rulings are on #1997 and in
  [OWNER_RULINGS.md](../planning/OWNER_RULINGS.md) under 2026-09-29.

## Non-decisions

- How a decision is applied to the inventory, and whether it ever is.
- Whether evidence may fill a record the module has not finished. The owner decides after
  the last wave of #1997.
- A read contract over evidence for personal access tokens or the MCP server.
- Whether a conflict is ever a finding in the validation engine (ADR 0024).
