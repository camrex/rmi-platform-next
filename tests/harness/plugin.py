"""pytest plugin: the database fixtures. Loaded by the root `conftest.py`.

Loop discipline (#1943, #1951): every async fixture and test runs on the function-scoped loop
(pinned in pyproject.toml). Nothing async is cached across tests: the engine is created and
disposed inside each test's own loop, with `NullPool`, so no connection can outlive its loop.
The only session-scoped fixture is synchronous and talks to the server through short-lived
`asyncio.run` calls whose engines are disposed before they return.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator, Iterator

import pytest
import pytest_asyncio
from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from tests.harness import db


@pytest.fixture(scope="session")
def migration_chains() -> list[db.Chain]:
    """The chains built into the scratch database: core and every module. A test directory may
    override this fixture (tests/harness does, with its sample chain)."""
    return db.discover_chains()


@pytest.fixture(scope="session")
def scratch_database_url(migration_chains: list[db.Chain]) -> Iterator[URL]:
    """A scratch database for the whole session, built by running every migration chain to head.

    Skips the dependent tests when the server is unreachable, unless RMI_REQUIRE_DB=1 (then it
    fails, so CI that has a server cannot silently skip).
    """
    admin = db.admin_url()
    problem = asyncio.run(db.server_error(admin))
    if problem is not None:
        message = f"PostgreSQL not available ({problem}); see docs/TESTING.md"
        if os.environ.get(db.REQUIRE_DB_ENV) == "1":
            pytest.fail(message, pytrace=False)
        pytest.skip(message)
    name = db.new_scratch_name()
    asyncio.run(db.create_scratch_database(admin, name))
    url = db.scratch_url(admin, name)
    try:
        db.upgrade(url, migration_chains)
        yield url
    finally:
        asyncio.run(db.drop_scratch_database(admin, name))


@pytest_asyncio.fixture
async def db_engine(scratch_database_url: URL) -> AsyncIterator[AsyncEngine]:
    """An engine on this test's loop. Disposed at teardown."""
    engine = create_async_engine(scratch_database_url, poolclass=NullPool)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    """A session whose work is rolled back at the end of the test, however the test ends.

    The session joins an outer transaction held by the fixture; `session.commit()` inside the
    test only releases a SAVEPOINT, so tests may commit freely and nothing persists.
    """
    async with db_engine.connect() as conn:
        outer = await conn.begin()
        session = AsyncSession(
            bind=conn, join_transaction_mode="create_savepoint", expire_on_commit=False
        )
        try:
            yield session
        finally:
            await session.close()
            await outer.rollback()
