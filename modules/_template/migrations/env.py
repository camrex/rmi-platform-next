"""Alembic env for the {{MODULE_KEY}} chain (docs/CONTRACT.md "Storage"). Do not edit; the rules:

- the URL comes from `config.attributes["url"]` (set by `tests.harness.db.upgrade`), falling back
  to `sqlalchemy.url` for the alembic CLI;
- each chain keeps its own version table (`alembic_version_<chain>`), so chains in one database
  do not see each other's revisions;
- no `target_metadata` is used to create anything: the schema is whatever the revisions say.
"""

import asyncio

from alembic import context
from sqlalchemy.engine import Connection, make_url
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

VERSION_TABLE = "alembic_version_{{MODULE_KEY}}"
config = context.config


def _url() -> str:
    attr = config.attributes.get("url")
    return str(attr) if attr else config.get_main_option("sqlalchemy.url") or ""


def _run(connection: Connection) -> None:
    context.configure(connection=connection, version_table=VERSION_TABLE)
    with context.begin_transaction():
        context.run_migrations()


async def _run_async() -> None:
    engine = create_async_engine(make_url(_url()), poolclass=NullPool)
    async with engine.connect() as connection:
        await connection.run_sync(_run)
    await engine.dispose()


asyncio.run(_run_async())
