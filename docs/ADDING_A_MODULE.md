# Adding a module

PROPOSAL §3.3, written against what B1.12–B1.14 built and walked through on 2026-10-03 with a
throwaway module (generate, sync, test, migrations, isolation). Every command runs from the repo
root in a new session. Examples use the key `shed`; replace it. Field meanings: `docs/CONTRACT.md`.
Worked examples: `modules/hello` (offers a seam), `modules/hello_friend` (uses it).

A module is one folder, `modules/<key>/`, plus `contracts/<key>_*` for the seams it offers.
**Nothing else changes** (`make check-isolation`, step 8). A TIVS asset type is *not* a platform
module; it is a sub-module of TIVS (PROPOSAL §8.2).

## 1. Generate it

    uv run python scripts/new_module.py shed
    make sync

`<key>` is `^[a-z][a-z0-9_]*$` and not `core`, `api`, `static`, `admin`, `auth`. `make sync` installs
the new workspace member; without it the `rmi.modules` entry point does not exist and `describe`
and the contract test cannot find the module. Check:

    uv run pytest modules/shed            # 2 passed (contract + page)
    uv run rmi describe --compact         # "load_order" lists "shed"

You get `manifest.py`, `web.py` (one page at `/shed/`, nav item "Shed"), `README.md`,
`pyproject.toml` (entry point `shed = "modules.shed.manifest:manifest"`), an empty
`migrations/__init__.py`, and `tests/test_contract.py` + `tests/test_page.py`. Edit the
`description`, `display_name` and `accent` in `manifest.py` and the README now.

## 2. Storage (skip if the module owns no tables)

Declare `db_schema="shed"` and `migrations="shed/migrations"` together (the manifest rejects one
without the other); add `core_revision=">=0005"` only once core has revisions. The core does not
yet act on these fields; the harness finds chains by folder, so the folder rules matter:

1. `modules/shed/migrations/env.py`: copy `tests/harness/sample_chain/env.py` and change
   `VERSION_TABLE` to `alembic_version_shed` (URL from `config.attributes["url"]`, own version table).
2. `modules/shed/migrations/versions/0001_<what>.py`: create schema `shed` and the tables in it.
3. `modules/shed/migrations/metadata.py` defining `target_metadata`, the `MetaData` of your models
   (tables with `schema="shed"`). Models are `modules/shed/models.py`.
4. Never `create_all` (a test fails the build on it); the schema comes only from migrations.

Check: `make check-migrations` upgrades core and every chain in a scratch database and fails on any
drift between migrations and `target_metadata`. It needs PostgreSQL (`docs/TESTING.md`); without it
the check skips with a message. Write DB tests with the `db_session` fixture.

## 3. Routes, nav, permissions

In `web.py` (split into `web/` before 500 lines) add routes to the router. The core mounts it under
`/shed/`, so route paths are relative: `@router.get("/bungalows")` is `/shed/bungalows`. Give each
route a `name="shed.<page>"`. For each page add `Nav("Label", "/shed/<page>", facet=...)` to `nav`
in `manifest.py`; a nav path is `/shed` or starts with `/shed/`. Any `facet` used by `nav` or a link kind must
also be declared: `permissions=Permissions(facets=["edit:inventory"])`. Dangerous powers are
`capabilities`; keys with roles but no pages are `access_keys`. Pages return HTML; no module
imports another, and no hand-built links to other modules' paths (step 4).

Check: `uv run pytest modules/shed`. Add a test for each page in `tests/` (the template's
`test_page.py` shows how: a bare `FastAPI` with the router included under `/shed`).

## 4. What it needs from others

Every need is declared, never imported:

| need | declare | notes |
|---|---|---|
| a seam it cannot run without | `requires=[SeamRef("catalog.items", ">=1,<2")]` | start-up fails, naming module and range, if nobody offers it |
| a seam that turns on a feature | `uses=[SeamRef("hello.greeting", ">=1,<2")]` | feature must degrade with a reason when absent; module still loads |
| a GIS dataset | `gis=[Slot("bungalow", dataset="bungalows", required=True)]` | read-only; `writable_fields` needs capability `gis.write_back` |
| a catalog item column | `catalog_refs=[CatalogRef("shed.instance", column="item_id")]` | table must be in your own schema |
| a card on your pages | `cards_hosted=[...]` | empty when the provider is absent |
| a core event | `on=[On("dataset.landed", "bungalows", hooks.adopt)]` | |

To consume a seam, import its **contract** only (`from contracts.hello_greeting.v1 import
GreetingV1`) and ask for the implementation or `None`. The core has no seam registry yet
(B2); until then read it as `modules/hello_friend/seams.py` does (a FastAPI dependency over
`app.state.seams`) so only that one function changes later. Pages must work with it absent
(`modules/hello_friend/web.py`); that is what step 6 tests.

## 5. What it offers

- **A seam**: (a) write the contract `contracts/shed_<name>/v1.py`: a `Protocol` plus frozen
  pydantic DTOs (`ConfigDict(frozen=True, extra="forbid")`), no implementation, `__all__`, and an
  `__init__.py`; the major version is in the file name; (b) implement it in `modules/shed/seams.py`;
  (c) declare `seams_offered=[SeamImpl("shed.<name>", "1.0", Impl())]`. Names start with the module
  key. Model: `contracts/hello_greeting/v1.py`, `modules/hello/seams.py`. `describe` publishes the
  JSON Schema of the DTOs. Breaking change = new `v2.py` and a new `SeamImpl`, never an edit of `v1`.
- **A link kind** (`links_offered`), relations, **cards** (`cards_offered`): declared the same way;
  the core does not render links or cards yet (B2), but the contract test already checks that no
  nav or link kind points at a module that is not loaded.
- **Jobs** (`jobs=[Job(fn, cron="0 6 * * *")]`, UTC) and **validation** providers likewise.

If you offer a seam, add a test that calls the implementation through the contract type (see
`modules/hello/tests/test_hello.py`).

## 6. Prove it

    uv run pytest modules/shed

`tests/test_contract.py` (already there; do not edit) calls `assert_contract(manifest)`. For each
combination of your `uses` seams present or absent (all present, each absent alone, none present;
providers are the other installed modules) it builds an app and asserts: the set resolves and
exactly the absent `uses` are reported disabled; every page and nav path answers without a 5xx;
no nav, link kind or rendered link points at a module that is not loaded; `GET /api/v1/describe`
lists your module and nav. A failure lists every problem with its scenario.

Then the whole gate: `make check` (ruff, pyright strict, pytest, 500-line cap, core-is-clean,
migrations, decisions). `modules/_template` is excluded from lint and tests; your module is not.

## 7. Record decisions

A choice another session would need to know (a seam shape, a vocabulary, a rule from the operator)
goes in `docs/decisions/NNNN-<slug>.md` from `0000-template.md`, with `status` and `refs`
(`docs/decisions/README.md`; `make check-decisions`). Keep the module `README.md` to one page: what
it owns, what it offers and uses, how to test it. Add a row to the tables in `MAP.md` if the module
owns data.

## 8. Before the PR

    make check
    make check-isolation BASE=origin/main MODULE=shed

The second fails if the diff touches anything outside `modules/shed/`, `contracts/shed_*` and
`docs/`. A module PR edits no `core/` file; if you need one, that is a core task, not part of the
module. `uv.lock` is allowed.
