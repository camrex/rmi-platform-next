---
status: ruled
kind: architecture
date: 2026-06-03
refs: []
source_status: "Accepted (2026-06-03) · **Phase C active** (2026-06-07) · **Versioning scope settled** (2026-07-03)"
imported_from: rmi-platform/docs/adr/0006-branching-and-release-strategy.md
imported_on: 2026-10-03
---
# 0006 — Branching and release strategy

**Status**: Accepted (2026-06-03) · **Phase C active** (2026-06-07) · **Versioning scope settled** (2026-07-03)

## Update (2026-07-03) — one platform version, not per-module versions

Raised during TIVS 2.0 planning: a release bumps the platform version even for
modules that weren't touched. **Decided: keep the single platform SemVer.** The
version names the *deployable* — one container, one deploy, one rollback unit —
not any module. Per-module semver earns its ceremony only when a module ships or
deploys independently or has external consumers needing a compatibility matrix;
neither exists. Supporting practices:

- Conventional-commit scopes (`feat(tivs): …`) keep per-module change history
  derivable; release notes list the modules touched.
- **Audit tie-in**: valuation snapshots and job run-reports record the platform
  version + git SHA that produced them — a one-part answer to "which code
  produced this number."
- Reconsideration trigger: a module gaining independent deployment or external
  consumers.

## Update (2026-06-07) — the trigger fired; Phase C is now in force

SBIS went live in production with real data (2026-06-06), which is exactly the
trigger below. Direct-to-`main` (Phase A) ends here; **branch + PR + CI gate** and
**tag-driven releases** are now the working rules. Concretely:

- **Branch protection on `main`**: a PR and a passing CI run (`check`) are required to
  merge; no direct pushes; linear history (squash-merge). Required approvals are **0**
  while this is a single-developer repo (raise to 1 when a second contributor joins);
  `enforce_admins` is **off** so the owner retains a break-glass path — used by
  exception, not as routine.
- **Branches**: short-lived `feat/ fix/ chore/ docs/`, squash-merged within a day or two.
- **Releases = prod deploys.** `main` is always deployable. To ship, tag a **SemVer**
  release `vMAJOR.MINOR.PATCH` on `main` and cut a GitHub Release (notes auto-generated
  from the squashed PR titles); deploy **that tag's commit SHA** per
  [DEPLOYMENT.md](../DEPLOYMENT.md) (images are already SHA-tagged, so the release pins
  the exact artifact). **`v1.0.0`** marks the production baseline. Deploy is **manual on
  release** for now; a release-triggered GitHub Action (build → push → deploy) is a later
  option once cadence justifies storing AWS deploy creds as GH secrets.
- **Migrations** follow the Phase C rules below. The one gap vs the ideal: there is **no
  staging DB** yet — migrations are tested on the local Docker Postgres and applied on
  deploy (the `api` container migrates before serving). A throwaway Lightsail staging box
  remains a "could do" for rehearsing migrations against prod-like data.

The original decision (unchanged) follows.

## Context

The project is greenfield: nothing is deployed, there is no real data, and work
is currently a single developer across two workstations. Committing directly to
`main` is efficient and appropriate now. But the platform will eventually back
hosted environments and live production data (SBIS in production; TIVS/CVS
migration waves), at which point direct commits to a deployable `main` become
unsafe. This ADR fixes the **trigger** for tightening process, not the mechanics,
which can evolve.

Gitflow (long-lived `develop`/`release` branches) is explicitly rejected: it is
overhead a continuously-deployed modular monolith does not need.

## Decision

Adopt **trunk-based development with short-lived feature branches**, phased by a
single clear trigger.

**The trigger:** *the first time `main` backs a hosted environment (even a
Lightsail staging box) or reads/writes real data, branch + PR + CI-gate becomes
mandatory.* Everything before that point may stay direct-to-`main`.

### Phase A — now (greenfield; nothing deployed, no real data)

- Direct commits to `main`. `main` is the working trunk.
- Cross-machine discipline: `git pull && uv sync` when switching workstations;
  push before stepping away (see ADR 0001 / cross-machine setup).

### Phase B — `main` first backs a hosted environment, or a second contributor joins

- All changes via short-lived branches (`feat/…`, `fix/…`, `chore/…`), merged
  within a day or two, **squash-merged** to keep `main` linear.
- **Branch protection on `main`**: require a PR and a passing CI run before
  merge; no direct pushes. CI (`.github/workflows/ci.yml`) already runs on PRs.
- `/code-review` on the diff becomes part of the loop.

### Phase C — live production data (SBIS prod; TIVS/CVS waves)

Phase B rules become hard requirements, plus data-specific guardrails:

- `main` is always deployable; deploy from `main` by tag/SHA.
- **Migrations** are the sharp edge: every migration is reviewed in a PR, tested
  against a staging DB that mirrors prod *before* prod, forward-only, with a
  rehearsed rollback. This is parity-gate #5 in the
  [parity matrix](../planning/IDEAL_PLATFORM_PARITY_MATRIX.md).
- Prefer **expand/contract** migrations (add new → backfill → switch → drop
  later) so a bad deploy is recoverable; never run a destructive migration
  directly against prod.

## Consequences

- Low ceremony now; process tightens exactly when risk appears, not before.
- Branch protection is a GitHub setting layered on the existing CI gate when the
  trigger fires (configurable via `gh`); harmless to enable earlier if desired.
- Squash-merge keeps history readable but loses intra-branch granularity — an
  accepted trade for a linear, bisectable `main`.
- Triggers are deliberately event-based (deploy / real data / second contributor)
  rather than date-based, so they fire when they actually matter.
