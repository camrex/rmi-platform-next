# Testing

`make check` runs everything (ruff, pyright strict, pytest, size and core-clean checks). This page
is about the database tests. Code: `tests/harness/`, loaded by the root `conftest.py`.

## The database

The box runs PostgreSQL 18 (the live platform runs 18.x). Database `rmi`, role `rebuild`
(CREATEDB, not superuser), peer auth over the socket:

    postgresql://rebuild@/rmi?host=/var/run/postgresql

Override with `RMI_TEST_ADMIN_DSN`. `rmi` itself is never written to: it is only the database the
harness connects to in order to `CREATE DATABASE`. If `psql -d rmi -c 'select 1'` fails, the
operator runs `rmi-fleet deploy/rebuild-postgres.sh`. No pgserver (it is PG 16), no docker.
PostGIS is not used yet; the GIS-sync phase (B3) decides how to get it.

## Fixtures (`tests/harness/plugin.py`)

| fixture | scope | what |
|---|---|---|
| `migration_chains` | session | the Alembic chains to build: core and every module (`db.discover_chains`). A test directory may override it (tests/harness does, with a sample chain). |
| `scratch_database_url` | session | `CREATE DATABASE rmi_test_<pid>_<hex>`, run every chain to `head`, drop it (WITH FORCE) at the end. Sync fixture. |
| `db_engine` | function | async engine (asyncpg, `NullPool`) on the test's own loop, disposed at teardown. |
| `db_session` | function | `AsyncSession` inside an outer transaction with `join_transaction_mode="create_savepoint"`; rolled back after the test. `session.commit()` only releases a savepoint, so tests may commit and nothing persists. |

Use them as plain arguments; tests are `async def` with no marker (asyncio mode auto):

```python
async def test_something(db_session: AsyncSession) -> None:
    await db_session.execute(text("insert into ..."))
```

## Rules this harness enforces, and why

- **One event loop per test** (#1943, #1951: half of CI runs failed with asyncpg "attached to a
  different loop"). `pyproject.toml` pins `asyncio_mode = "auto"`, `asyncio_default_fixture_loop_scope`
  and `asyncio_default_test_loop_scope` to `function`, and disables the anyio plugin (`-p no:anyio`);
  pytest-asyncio is the only async runner. No async fixture is session-scoped, no engine is cached
  in a module global, `NullPool` means no connection outlives its loop. Do not add
  `@pytest.mark.anyio`, and do not create an engine at import time.
- **Schema only from migrations** (#928: a schema built from models drifted from the migrations).
  `scratch_database_url` runs `alembic upgrade head`; a test fails the build if any Python file
  under `core/ contracts/ modules/ scripts/ tests/` calls `create_all`.
- **Chain convention** a chain is `migrations/` with `env.py` and `versions/` (under
  `core/src/<pkg>/` or `modules/<key>/`, never `_template`). Its `env.py` takes the URL from
  `config.attributes["url"]` (falling back to `sqlalchemy.url`) and keeps its own version table,
  `alembic_version_<chain>`. `tests/harness/sample_chain/env.py` is the model. Alembic runs in a
  worker thread (`db.upgrade_async`) or synchronously in the session fixture, never inside a test's loop.
- **No server, no silent pass.** If PostgreSQL is unreachable, database tests skip with the reason;
  with `RMI_REQUIRE_DB=1` they fail instead. Set it wherever a server is expected.

## CI

`.github/workflows/ci.yml` has no PostgreSQL service yet, so database tests skip there. When CI
gets one, set `RMI_TEST_ADMIN_DSN` and `RMI_REQUIRE_DB=1` in the workflow (a follow-up for the
operator or B1.15, which needs the same server).
