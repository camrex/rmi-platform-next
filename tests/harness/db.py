"""Database helpers for tests: scratch databases, migrations, chain discovery.

No pytest in here. The schema is only ever built by running Alembic chains (#928); nothing in
the repo builds a schema from models, and `test_db_harness.py` fails if anything does.
"""

from __future__ import annotations

import asyncio
import os
import secrets
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from rmi_core.manifest import ModuleManifest

# The box's PostgreSQL 18, peer auth over the socket (docs/TESTING.md).
DEFAULT_ADMIN_DSN = "postgresql://rebuild@/rmi?host=/var/run/postgresql"
ADMIN_DSN_ENV = "RMI_TEST_ADMIN_DSN"
REQUIRE_DB_ENV = "RMI_REQUIRE_DB"
REPO_ROOT = Path(__file__).resolve().parents[2]


def admin_url() -> URL:
    """Async URL of the database the scratch databases are created from."""
    url = make_url(os.environ.get(ADMIN_DSN_ENV, DEFAULT_ADMIN_DSN))
    return url.set(drivername="postgresql+asyncpg")


def scratch_url(admin: URL, name: str) -> URL:
    return admin.set(database=name)


def new_scratch_name() -> str:
    return f"rmi_test_{os.getpid()}_{secrets.token_hex(3)}"


async def server_error(url: URL) -> str | None:
    """None if `select 1` works against `url`, else why not."""
    engine = create_async_engine(url, poolclass=NullPool, connect_args={"timeout": 3})
    try:
        async with engine.connect() as conn:
            await conn.execute(text("select 1"))
        return None
    except Exception as exc:
        return f"{type(exc).__name__}: {exc}"
    finally:
        await engine.dispose()


async def _admin_execute(admin: URL, statement: str) -> None:
    # CREATE/DROP DATABASE cannot run inside a transaction block.
    engine = create_async_engine(admin, isolation_level="AUTOCOMMIT", poolclass=NullPool)
    try:
        async with engine.connect() as conn:
            await conn.execute(text(statement))
    finally:
        await engine.dispose()


async def create_scratch_database(admin: URL, name: str) -> None:
    await _admin_execute(admin, f'CREATE DATABASE "{name}"')


async def drop_scratch_database(admin: URL, name: str) -> None:
    await _admin_execute(admin, f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')


@dataclass(frozen=True)
class Chain:
    """One Alembic chain: `core` or one module (ADR 0002). `location` holds env.py + versions/."""

    name: str
    location: Path


def discover_chains(root: Path = REPO_ROOT) -> list[Chain]:
    """Chains by convention: a `migrations/` directory with `env.py` and `versions/` under
    `core/src/<pkg>/` or `modules/<key>/` (not `_template`). Core first, then modules by name."""
    found: list[Chain] = []
    for base, label in ((root / "core" / "src", "core"), (root / "modules", "")):
        if not base.is_dir():
            continue
        for env in sorted(base.glob("**/migrations/env.py")):
            location = env.parent
            parts = location.relative_to(root).parts
            if "_template" in parts or not (location / "versions").is_dir():
                continue
            name = label or parts[1]
            found.append(Chain(name=name, location=location))
    return found


def manifest_chain_problems(
    manifests: Iterable[ModuleManifest], root: Path = REPO_ROOT
) -> list[str]:
    """A module's chain lives at `modules/<key>/migrations/` (`env.py` + `versions/`), always.
    The manifest says whether there is one: `db_schema` is set exactly when the chain exists, so
    neither can be forgotten or left behind. One line per problem; empty when they agree."""
    problems: list[str] = []
    for m in manifests:
        location = root / "modules" / m.key / "migrations"
        has_chain = (location / "env.py").is_file() and (location / "versions").is_dir()
        if m.db_schema is not None and not has_chain:
            problems.append(
                f"{m.key}: declares db_schema={m.db_schema!r} but modules/{m.key}/migrations/ "
                "has no env.py and versions/"
            )
        if m.db_schema is None and has_chain:
            problems.append(
                f"{m.key}: modules/{m.key}/migrations/ is a chain but the manifest has no db_schema"
            )
    return problems


def upgrade(url: URL, chains: list[Chain]) -> None:
    """`alembic upgrade head` for each chain, in order, against `url` (synchronous: Alembic's
    env.py runs its own loop, so never call this from inside a running event loop).

    env.py convention: read the URL from `config.attributes["url"]`, falling back to the
    `sqlalchemy.url` option so the same env.py works from the alembic CLI."""
    for chain in chains:
        config = Config()
        config.set_main_option("script_location", str(chain.location))
        config.attributes["url"] = url.render_as_string(hide_password=False)
        command.upgrade(config, "head")


async def upgrade_async(url: URL, chains: list[Chain]) -> None:
    """`upgrade` from async code: Alembic's env.py needs its own event loop, so it runs in a
    worker thread."""
    await asyncio.to_thread(upgrade, url, chains)
