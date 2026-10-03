---
status: ruled
kind: architecture
date: 2026-08-06
refs: []
source_status: "Accepted (2026-08-06) · **Shipped**: the DR half in v1.19.0 (#7) ·"
imported_from: rmi-platform/docs/adr/0021-backup-restore-and-data-durability.md
imported_on: 2026-10-03
---
# 0021 — Backup, restore & data durability: DR vs project archives

**Status**: Accepted (2026-08-06) · **Shipped**: the DR half in v1.19.0 (#7) ·
**Refines**: ADR 0016 (sync provenance is part of the durable record) ·
**Informed by**: the 2026-07-23 GIS/durability discussion (#455), owner
decisions 2026-08-06; supersedes the mechanism notes scattered in #7/#9/#407.

## Context

The platform's durable record today is: Lightsail's 7-day automated DB
snapshots, a pre-deploy manual snapshot in the deploy runbook, S3 for
files (photos/plans/docs), and dev-machine dump/restore tooling
(`deploy/db_backup.sh` / `db_restore.sh`). That covers "the database died
yesterday" and nothing else. Two very different products hide under the word
"backup", and conflating them produced most of the past confusion:

| | Disaster recovery | Project archive |
| --- | --- | --- |
| Unit | whole system | one project, across every schema |
| Trigger | scheduled | engagement close |
| Horizon | days–weeks | indefinite (litigation support) |
| Restore target | same version, fast | possibly years later, version skew |
| Integrity bar | recent + restorable | evidentiary (checksums, immutability) |

RMI's appraisal work makes the second product a real obligation: a valuation
may be litigated long after the engagement closes, and the record that matters
is **what we saw** — including the project's synced GIS rows, which the Portal
will have moved past (ADR 0016: sync provenance is never pruned by the
application; since its 2026-09-16 amendment a platform admin may delete sync
runs nothing stands on, audited).

## Decision

### 1. Two products, built separately, sharing one capsule grammar

Disaster recovery and project archives are separate mechanisms with separate
triggers and lifetimes. They share one convention: **nothing lands in S3
without a metadata capsule** (§4) describing exactly what it is and what
would be needed to read it again.

### 2. Disaster recovery: scheduled logical dump to S3 (#7)

A worker cron task runs `pg_dump -Fc` (all schemas — platform + every module —
including the six `alembic_version*` tables) and uploads to the private
platform bucket:

```text
backups/daily/rmi_platform-YYYY-MM-DD.dump        (+ .meta.json capsule)
backups/monthly/rmi_platform-YYYY-MM-01.dump      (first-of-month copy)
```

- Retention is an **S3 lifecycle rule**, not app code: expire `backups/daily/`
  after **14 days**, `backups/monthly/` after **12 months** (owner-adjustable;
  the app only ever needs `s3:PutObject` on the `backups/` prefix — no delete
  permission, which also means a compromised app credential cannot destroy
  history).
- The task is disabled by a negative configured hour (the `gis_resync_hour_utc`
  pattern) so dev stacks don't wake up to fail nightly.
- Lightsail's native snapshots stay on as the fast same-provider restore path;
  the S3 dumps are the longer-horizon, provider-independent one.
- Restore procedure (scratch-DB verified) lives in the deploy runbook and
  reuses the dev tooling's conventions: restore, then run the migrate role to
  reach head (serve never migrates, #418).

### 3. Project archive: archive-then-offboard (owner decision 2026-08-06)

When an engagement closes, the project is exported to an immutable capsule and
**then leaves the live database**. Restore = rehydration from the capsule.
Consequences we accept:

- The live DB stays lean (bounded by active engagements, not history).
- The litigation record is the capsule, so the capsule must be complete:
  every project-keyed row in every schema, the project's synced GIS rows and
  sync-run provenance, the project's S3 prefix, the §4 metadata, **and the
  runtime to read it all** — a reference to the release's saved image (§5)
  plus a snapshot of the compose file that runs it. Five years out, the
  restore is: load the saved image, compose up against the rehydrated DB,
  read-only — the app exactly as it was, no live secrets, no Portal needed.
- Evidentiary posture: per-file SHA-256 manifest inside the capsule, uploaded
  to an S3 storage class with object lock / immutability, never overwritten.
- Rehydration is a **first-class, tested path** — offboarding without a proven
  restore is deletion with extra steps. The archive mechanism does not ship
  until a round-trip (archive → wipe → rehydrate → spot-check) passes on a
  real project copy.

The archive mechanism is **not built yet**; this ADR fixes its shape so the DR
slice (§2) and release process (§5) record the right things starting now.

### 4. The restore-context capsule: record now, unobtainable later

Every dump/archive carries a small JSON capsule written at capture time:

- platform version (`__version__`) and image tag,
- the six alembic chain heads *as stored in the dumped DB*,
- the enabled-module set per project (archives) or globally (DR),
- capture timestamp, dump SHA-256, dump size,
- for archives: the project code/id and the sync-run high-water marks.

This costs one small file per capture and is the difference between "a dump"
and "a restorable record" once versions have moved.

### 5. Version skew: resurrect the era, then migrate forward

An archive captured on 1.7.5 may need to be read on 1.9.0's watch. Primary
path: **run the archived release against the rehydrated data, read-only** —
the capsule references the release image, and unconfigured GIS degrades
gracefully (DB-first surfaces work offline, ADR 0016). Migrating the data
forward to current is the optimization, attempted when the chains permit.

This requires **per-release image custody**: at release time, `docker save`
the tagged image to `s3://…/images/` once per version (Lightsail's registry
evicts old images). Cheap at release time; impossible to reconstruct honestly
later. Rides the release runbook as one step.

Archives **reference** the saved image rather than bundling a copy — images
are deduplicated across the many projects that close on the same version, and
the `images/` prefix sits under the same immutability posture as the archives
themselves. (If a specific engagement warrants a fully self-contained capsule,
copying the referenced image into it is a one-command opt-in, not a design
change.)

## Consequences

- #7 becomes implementable exactly as §2 (first slice, in flight with this
  ADR); #455 tracks the archive mechanism (§3–§5) as follow-on issues:
  capsule exporter, rehydration runner, image-custody release step.
- The release runbook gains the `docker save` step (§5) — start doing this at
  the next release even though the archive reader doesn't exist yet.
- Owner-adjustable knobs live in one place: retention counts (§2), archive
  storage class (§3).
- Rejected: hand-rolled retention deletes in app code (lifecycle rules are
  simpler and safer under least privilege); pruning sync provenance to save
  space (ADR 0016 forbids it); "archive but keep live" (owner decision —
  revisit only if rehydration proves too slow for a real recall).
- **Amended 2026-09-16 (#1499).** The rejection of pruning sync provenance
  stands for *application code*: nothing deletes sync history on a schedule or
  a retention count. It no longer covers an admin's choice. A platform admin
  may delete sync runs (and their gap rows) that no current landing,
  derivation or valuation snapshot stands on, from Admin → Sync history, and
  every deletion is audited in the same transaction (ADR 0016's amendment of
  the same date). A project archive therefore captures the provenance of what
  its valuations stand on, which the delete cannot remove, plus whatever older
  history no admin chose to delete.
- **Amended 2026-09-17 (#1916).** §2's parenthesis — *"the app only ever needs
  `s3:PutObject` on the `backups/` prefix — no delete permission, which also
  means a compromised app credential cannot destroy history"* — described a
  posture that was never implemented. `deploy/iam/app-policy.json` granted
  `s3:DeleteObject` on `arn:aws:s3:::rmi-platform/*`, which includes
  `backups/*`, and the live `rmi-platform-app` user carried the same grant
  verbatim (simulated 2026-09-17: `s3:DeleteObject` on
  `backups/daily/rmi_platform-2026-09-17.dump` returned **allowed**). The
  policy now carries an explicit `Deny` on `s3:DeleteObject` and
  `s3:DeleteObjectVersion` for `arn:aws:s3:::rmi-platform/backups/*` and
  `arn:aws:s3:::rmi-platform/*/backups/*` (the second covers a set
  `RMI_STORAGE_S3_PREFIX`, which production does not use) — a `Deny` rather than
  a narrowed `Allow`, so widening the `Allow` beside it cannot silently
  re-grant what this ADR forbids. The `DeleteObject` grant on the app's own
  prefixes stays: the PM shelf purges an object after its row commits and the
  SBIS plan replace path overwrites in place. **Read this as the ADR now
  describing reality rather than intent** — until 2026-09-17 it described only
  intent, and nothing in the repo read as wrong.
