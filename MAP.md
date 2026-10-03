# MAP — where things live

Orientation for a new session, written 2026-10-03 after phase B1 (harness and contract). Design:
`docs/architecture/PROPOSAL.md`; what is approved: `approvals/architecture.md` and
`docs/decisions/0101-*.md`. Rules for unattended runs: `AGENTS.md`. Update this file when you add
a directory, a core service or a module.

## Layout

| path | what |
|---|---|
| `core/src/rmi_core/` | the core package (`rmi-core`). **No module key may appear in it** (`make check-core-clean`). |
| `core/src/rmi_core/manifest.py` | `ModuleManifest` and its parts (`SeamRef`, `SeamImpl`, `Nav`, `Slot`, `Job`, `On`, `LinkKind`, `Card`, `CatalogRef`, ...). Field meanings: `docs/CONTRACT.md`. |
| `core/src/rmi_core/resolve.py` | pure: manifests -> load order; unmet `requires` fail, absent `uses` disable a feature, duplicates and cycles rejected. |
| `core/src/rmi_core/loader.py` | `load_modules()`: finds manifests via the `rmi.modules` entry point, resolves. The one function web and worker roots will both call. |
| `core/src/rmi_core/describe.py` | `GET /api/v1/describe` and `rmi describe [--compact]`: modules, routes, nav, link kinds, seams with JSON Schemas, permissions, jobs. |
| `core/src/rmi_core/refs.py` | `Ref` (`gis:`, `oid:`, `<module>.<kind>:`, `catalog.item:`, `pricing.price:`). |
| `core/src/rmi_core/testing/contract.py` | `assert_contract(manifest)`: the test every module runs. |
| `contracts/<key>_<name>/v<major>.py` | seam contracts: a `Protocol` plus frozen pydantic DTOs, no implementation. Owned by the module that offers the seam. Today: `hello_greeting`. |
| `modules/<key>/` | one module = one folder = one uv workspace member with an `rmi.modules` entry point. Today: `hello`, `hello_friend`. |
| `modules/_template/` | what `scripts/new_module.py` copies. Not a workspace member, not linted or tested. |
| `scripts/` | `new_module.py`, and the checks `make check` runs: `check_file_size.py` (500-line cap), `check_core_clean.py`, `check_migrations.py`, `check_decisions.py`; `check_module_isolation.py` (CI on module branches, needs `BASE` and `MODULE`); `import_adrs.py` (one-off). |
| `tests/harness/` | the pinned async + database harness (`docs/TESTING.md`); `tests/scripts/` tests the scripts. |
| `docs/` | `CONTRACT.md`, `ADDING_A_MODULE.md`, `TESTING.md`, `TOOLCHAIN.md`, `PARITY.md` (old-platform changes to replay), `architecture/PROPOSAL.md`, `inventory/` (what the old platform and its GIS look like), `decisions/` (the decision store, `docs/decisions/README.md`). |
| `data/` | operator-supplied only; nothing in it is committed. |
| `PLAN.md`, `JOURNAL.md`, `MISSION.md`, `runner/` | the unattended-run machinery. Not product code. |

Not built yet (B2 onward): the app and worker roots, seam registry (`seams.get(Contract)`), link
store, cards, events, access, settings, GIS sync. The contract declares them; the core does not
act on those fields yet. Today a module's routers are mounted only by the test app in
`testing/contract.py`.

## Who owns which data

| data | owner | status |
|---|---|---|
| a module's tables | that module: Postgres schema `<db_schema>` and its own Alembic chain (`modules/<key>/migrations/`, version table `alembic_version_<key>`) (ADR 0002) | convention built (B1.6, B1.15); `hello*` have no tables |
| core tables (identity, access, projects, audit, settings) | `rmi_core` chain, schema `core` | B2, not built |
| synced GIS copies | the core's sync engine; modules read them through `gis=[Slot(...)]` | B3 |
| catalog items and classes, prices and indexes | modules `catalog`, `pricing`; others reference them (`CatalogRef`, `pricing.price:` refs), never copy | B6, B8 |
| a seam's shape | the offering module, in `contracts/<key>_*`; consumers import only the contract | built (`hello_greeting`) |
| decisions | `docs/decisions/`, status `ruled | tabled | open | superseded` | built |
| GIS schema (Portal layers, domains, Survey123) | `rmigis-pyt`, operator and GIS admin; this repo only drafts proposals | never edited here |

Modules never import each other. Across a module boundary: a seam, a link, a card, or a catalog
reference.

## How to test

Everything goes through `uv` and `make` (both in `~/.local/bin`; the Makefile adds it to PATH).

| to | run |
|---|---|
| everything CI runs (sync, ruff, pyright strict, pytest, size, core-clean, migrations, decisions) | `make check` |
| install workspace members after adding or generating a module (needed for the entry point) | `make sync` |
| one module | `uv run pytest modules/<key>` |
| core | `uv run pytest core/tests` |
| see what the platform loaded | `uv run rmi describe --compact` |
| migrations from scratch + no drift | `make check-migrations` (needs PostgreSQL; skips with a message if unreachable, `RMI_REQUIRE_DB=1` makes that a failure) |
| a module PR touches only its own files | `make check-isolation BASE=origin/main MODULE=<key>` |

Database tests use scratch databases built from migrations only, one event loop per test
(`docs/TESTING.md`). Every module's `tests/test_contract.py` is two lines calling
`assert_contract(manifest)`; do not edit it.

## Conventions

- Layout per module: `manifest.py`, `web.py` (or `web/`), `seams.py`, `models.py`, `service/`,
  `jobs.py`, `migrations/`, `tests/`, `README.md`. Only what exists is created.
- Files at most 500 lines. pyright strict on `core`, `contracts`, `modules`, `scripts`, `tests`.
- Names other modules see are `<key>.<name>`; URL paths start with `/<key>/`.
- Adding a module: `docs/ADDING_A_MODULE.md`.
