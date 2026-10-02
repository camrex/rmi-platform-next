# Toolchain

Checked on `rmi-nuc` (Ubuntu 26.04, x86_64, user `rebuild`, no sudo), 2026-10-02.

## What the box had, and what B1.1 did

| tool | found | action |
|---|---|---|
| python3 | 3.14.4 at `/usr/bin`; no `pip`, no `ensurepip` (venv module exists) | not used; ADR 0002 pins 3.12 |
| python 3.12 | none | `uv python install 3.12` → 3.12.15 under `~/.local/share/uv` |
| uv | none | installed 0.12.22 from the GitHub release tarball to `~/.local/bin` |
| make | none (not in the base image) | `apt-get download make` + `dpkg -x` (no root) → `~/.local/bin/make` 4.4.1 |
| ruff, pyright, pytest | none | come from `uv sync` into `.venv` (ruff 0.16, pyright 1.1.414, pytest 9.1, pytest-asyncio 1.4) |
| git | `/usr/bin/git` | — |
| node / npm | `~/.local/node/bin` | pyright fetches nothing from it; not otherwise needed yet |
| docker | `/usr/bin/docker`, but `rebuild` is not in the `docker` group (socket permission denied) | unusable |
| PostgreSQL | none at B1.1; since B1.6 PostgreSQL 18.6 with role `rebuild` (CREATEDB), peer auth on the socket | used by the test harness: docs/TESTING.md |
| gh | none | not needed |

Outbound access to PyPI and GitHub works; `apt-get download` works (no install).

## Choice: uv workspace

The root `pyproject.toml` is a uv workspace (members `core` and `modules/*`, minus
`modules/_template`), as in the old platform (ADR 0001) and PROPOSAL §5. Reasons: each module is a
real package with its own `pyproject.toml` and `rmi.modules` entry point, which is what the loader
(B1.10) discovers; one lockfile (`uv.lock`, committed) and one `.venv`; and `uv` also supplies
Python 3.12, which the box's system Python cannot (no ensurepip). A plain venv would have meant
hand-installing every module. The root is not installable (`package = false`) and pins
`requires-python = ">=3.12,<3.13"`.

Ruff, pyright (strict) and pytest settings live in the root `pyproject.toml` only. Ruff skips
`runner/`, `data/` and `docs/`; pyright includes `core contracts modules scripts tests`.

## Use

```
make check      # sync, ruff check + format --check, pyright, pytest: the gate CI runs
make format     # ruff fix + format
```

`make` and `uv` are in `~/.local/bin`. The runner's `PATH` (`runner/run.py`) adds only
`~/.local/node/bin`, so a run may not find `make`. The Makefile puts `~/.local/bin` on its own
`PATH`, but `make` itself must be called as `~/.local/bin/make check` (or, for the operator,
`ln -s ~/.local/bin/make /usr/local/bin/make`, or add `~/.local/bin` to the runner's `PATH`).
Verified: `env -i PATH=/usr/bin:/bin ~/.local/bin/make check` passes.

## Missing — for the operator

1. **PostgreSQL (resolved, B1.6: the operator installed 18; the options below are history).** No server, no docker access. B1.6 (test database harness) and B1.15 (migrations
   check) need one. Pick one:
   - add `rebuild` to the `docker` group and say so (then `postgis/postgis` or `postgres:16`
     in a container); or
   - `sudo apt install postgresql postgresql-16-postgis-3` (or the 26.04 equivalents), and create
     a role and an empty database for tests; or
   - nothing: B1.6 may use the `pgserver` PyPI package, a self-contained PostgreSQL 16.2 that
     runs without root. Verified here (`uv run --with pgserver`, `select version()` works). It
     has no PostGIS, which the harness does not need before the GIS-sync phase; if PostGIS is
     wanted for tests, one of the first two is required.
   Tell the next run which, in `approvals/` or the task text; otherwise B1.6 will try `pgserver`.
2. **`make` on the system.** Optional: `sudo apt install make` makes `make check` work with the
   runner's `PATH` unchanged.
3. **Python 3.12 is uv-managed**, not a system package; if `~/.local/share/uv` is wiped, `make
   sync` reinstalls it (needs network).
