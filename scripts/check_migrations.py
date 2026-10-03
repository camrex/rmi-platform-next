#!/usr/bin/env python3
"""Migrations-from-scratch check (PROPOSAL §5; docs/TESTING.md).

Creates a scratch database, runs `alembic upgrade head` for core and then every module chain
(`tests.harness.db.discover_chains`), and asserts that each chain's schema equals its models: an
autogenerate comparison against the chain's `migrations/metadata.py` (`target_metadata`) must find
nothing to do. Nothing here builds a schema from models (#928).

A chain "owns" the tables that appeared in the database while it was upgraded (its version table,
`alembic_version*`, excepted). Other chains' tables are ignored when comparing, but a table the
chain created and its models do not declare is drift.

No chains: passes without touching a server. No server: prints why and passes, unless
RMI_REQUIRE_DB=1 (then it fails). Exit 0 = ok or skipped, 1 = problems.

    python scripts/check_migrations.py [--root DIR]
"""

from __future__ import annotations

import argparse
import asyncio
import importlib.util
import os
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from alembic.autogenerate import compare_metadata  # noqa: E402
from alembic.runtime.migration import MigrationContext  # noqa: E402
from sqlalchemy import MetaData, text  # noqa: E402
from sqlalchemy.engine import URL  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine  # noqa: E402
from sqlalchemy.pool import NullPool  # noqa: E402

from tests.harness import db  # noqa: E402

METADATA_FILE = "metadata.py"
_TABLES_SQL = text(
    "select table_schema, table_name from information_schema.tables "
    "where table_type = 'BASE TABLE' and table_schema not in ('pg_catalog', 'information_schema')"
)

TableKey = tuple[str | None, str]


def load_metadata(chain: db.Chain) -> MetaData | str:
    """The chain's `target_metadata`, or a message saying why there is none."""
    path = chain.location / METADATA_FILE
    if not path.is_file():
        return (
            f"no {METADATA_FILE} (it must define `target_metadata`, the chain's models' MetaData)"
        )
    spec = importlib.util.spec_from_file_location(f"_rmi_metadata_{chain.name}", path)
    if spec is None or spec.loader is None:
        return f"cannot load {path}"
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        return f"{METADATA_FILE} fails to import: {type(exc).__name__}: {exc}"
    metadata = getattr(module, "target_metadata", None)
    if not isinstance(metadata, MetaData):
        return f"{METADATA_FILE} has no `target_metadata` MetaData"
    return metadata


def _key(schema: str | None, name: str) -> TableKey:
    return (schema or None, name)


async def _tables(url: URL) -> set[TableKey]:
    engine = create_async_engine(url, poolclass=NullPool)
    try:
        async with engine.connect() as conn:
            rows = await conn.execute(_TABLES_SQL)
            found = {_key(schema if schema != "public" else None, name) for schema, name in rows}
    finally:
        await engine.dispose()
    return {k for k in found if not k[1].startswith("alembic_version")}


def _diffs(sync_conn: Any, metadata: MetaData, owned: set[TableKey]) -> list[str]:
    declared = {_key(t.schema, t.name) for t in metadata.tables.values()}

    def include_object(obj: Any, name: str | None, type_: str, reflected: bool, compare_to: Any):
        if not reflected:
            return True
        if type_ == "table":
            return _key(obj.schema, obj.name) in declared | owned
        table = getattr(obj, "table", None)
        if table is None:
            return True
        return _key(table.schema, table.name) in declared | owned

    context = MigrationContext.configure(
        sync_conn,
        opts={
            "compare_type": True,
            "compare_server_default": True,
            "include_schemas": True,
            "include_object": include_object,
        },
    )
    found: list[Any] = []
    for diff in compare_metadata(context, metadata):
        found.extend(diff if isinstance(diff, list) else [diff])  # type: ignore[reportUnknownArgumentType]
    return [repr(d)[:200] for d in found]


async def _drift(url: URL, metadata: MetaData, owned: set[TableKey]) -> list[str]:
    engine = create_async_engine(url, poolclass=NullPool)
    try:
        async with engine.connect() as conn:
            return await _run_diffs(conn, metadata, owned)
    finally:
        await engine.dispose()


async def _run_diffs(conn: AsyncConnection, metadata: MetaData, owned: set[TableKey]) -> list[str]:
    return await conn.run_sync(lambda sync_conn: _diffs(sync_conn, metadata, owned))


async def check_chains(chains: list[db.Chain], admin: URL) -> list[str]:
    """Upgrade every chain in a fresh scratch database, then compare each with its models.
    Returns the problems, empty if all is well. The scratch database is always dropped."""
    problems: list[str] = []
    name = db.new_scratch_name()
    await db.create_scratch_database(admin, name)
    url = db.scratch_url(admin, name)
    try:
        owned: dict[str, set[TableKey]] = {}
        upgraded: list[db.Chain] = []
        for chain in chains:
            before = await _tables(url)
            try:
                await db.upgrade_async(url, [chain])
            except Exception as exc:
                first_line = (str(exc).splitlines() or [""])[0]
                problems.append(
                    f"{chain.name}: upgrade head failed: {type(exc).__name__}: {first_line}"
                )
                continue
            owned[chain.name] = (await _tables(url)) - before
            upgraded.append(chain)
        for chain in upgraded:
            metadata = load_metadata(chain)
            if isinstance(metadata, str):
                problems.append(f"{chain.name}: {metadata}")
                continue
            problems.extend(
                f"{chain.name}: drift: {d}" for d in await _drift(url, metadata, owned[chain.name])
            )
    finally:
        await db.drop_scratch_database(admin, name)
    return problems


def run(root: Path) -> int:
    chains = db.discover_chains(root)
    if not chains:
        print("Migrations check: no migration chains found, nothing to check.")
        return 0
    admin = db.admin_url()
    unavailable = asyncio.run(db.server_error(admin))
    if unavailable is not None:
        if os.environ.get(db.REQUIRE_DB_ENV) == "1":
            print(f"Migrations check FAILED: PostgreSQL not available ({unavailable}).")
            return 1
        print(f"Migrations check SKIPPED: PostgreSQL not available ({unavailable}).")
        return 0
    problems = asyncio.run(check_chains(chains, admin))
    if problems:
        print("Migrations check failed:")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    print(f"Migrations check passed: {', '.join(c.name for c in chains)}.")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help="repo root to scan")
    sys.exit(run(parser.parse_args().root))


if __name__ == "__main__":
    main()
