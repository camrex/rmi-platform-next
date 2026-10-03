"""The harness itself: schema from migrations, per-test rollback, one loop per test, scratch
databases (#928, #1943, #1951)."""

import re
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from rmi_core.manifest import ModuleManifest
from rmi_core.testing.contract import installed_manifests
from tests.harness import db

ROOT = Path(__file__).resolve().parents[2]


async def test_schema_comes_from_the_migration_chain(db_session: AsyncSession) -> None:
    tables = await db_session.execute(
        text("select table_name from information_schema.tables where table_schema = 'public'")
    )
    names = {row[0] for row in tables}
    assert "harness_sample" in names
    assert "alembic_version_harness_sample" in names


async def test_scratch_database_is_not_the_admin_database(scratch_database_url: URL) -> None:
    assert scratch_database_url.database is not None
    assert scratch_database_url.database.startswith("rmi_test_")


async def test_rollback_part_1_writes_and_commits(db_session: AsyncSession) -> None:
    await db_session.execute(text("insert into harness_sample (label) values ('one')"))
    await db_session.commit()  # releases a savepoint only
    count = await db_session.scalar(text("select count(*) from harness_sample"))
    assert count == 1


async def test_rollback_part_2_sees_nothing(db_session: AsyncSession) -> None:
    count = await db_session.scalar(text("select count(*) from harness_sample"))
    assert count == 0


async def test_rollback_after_a_failing_statement(db_session: AsyncSession) -> None:
    with pytest.raises(Exception, match="not-null|null value"):
        await db_session.execute(text("insert into harness_sample (label) values (null)"))
    await db_session.rollback()
    assert await db_session.scalar(text("select 1")) == 1


@pytest.mark.parametrize("round_", [1, 2, 3])
async def test_every_test_gets_a_working_engine_on_its_own_loop(
    db_engine: AsyncEngine, round_: int
) -> None:
    # #1943/#1951: "attached to a different loop" showed up on the second test that touched
    # a cached engine. Three tests in a row must all connect.
    async with db_engine.connect() as conn:
        assert await conn.scalar(text("select cast(:n as integer)"), {"n": round_}) == round_


def test_postgres_is_18(scratch_database_url: URL) -> None:
    import asyncio

    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy.pool import NullPool

    async def version() -> str:
        engine = create_async_engine(scratch_database_url, poolclass=NullPool)
        try:
            async with engine.connect() as conn:
                return str(await conn.scalar(text("show server_version")))
        finally:
            await engine.dispose()

    assert asyncio.run(version()).startswith("18.")


def test_chain_discovery_skips_the_template(tmp_path: Path) -> None:
    for where in (
        "core/src/rmi_core/migrations",
        "modules/sbis/migrations",
        "modules/_template/migrations",
    ):
        (tmp_path / where / "versions").mkdir(parents=True)
        (tmp_path / where / "env.py").write_text("")
    (tmp_path / "modules/nover/migrations").mkdir(parents=True)
    (tmp_path / "modules/nover/migrations/env.py").write_text("")
    chains = db.discover_chains(tmp_path)
    assert [c.name for c in chains] == ["core", "sbis"]


def _manifest(key: str, *, schema: str | None) -> ModuleManifest:
    return ModuleManifest(
        key=key, version="1.0", display_name=key, accent="slate", db_schema=schema
    )


def _chain(root: Path, key: str) -> None:
    (root / "modules" / key / "migrations" / "versions").mkdir(parents=True)
    (root / "modules" / key / "migrations" / "env.py").write_text("")


def test_manifest_and_chain_folder_must_agree(tmp_path: Path) -> None:
    _chain(tmp_path, "both")
    _chain(tmp_path, "forgot_schema")
    (tmp_path / "modules" / "no_chain").mkdir()
    manifests = [
        _manifest("both", schema="both"),
        _manifest("forgot_schema", schema=None),
        _manifest("no_chain", schema="no_chain"),
        _manifest("neither", schema=None),
    ]
    problems = db.manifest_chain_problems(manifests, tmp_path)
    assert len(problems) == 2
    assert problems[0].startswith("forgot_schema:") and "no db_schema" in problems[0]
    assert problems[1].startswith("no_chain:") and "no env.py" in problems[1]


def test_installed_modules_agree_with_their_chain_folder() -> None:
    assert db.manifest_chain_problems(installed_manifests(), ROOT) == []


def test_nothing_builds_the_schema_from_models() -> None:
    """#928: a schema built with create_all drifts from the migrations. Forbidden everywhere."""
    pattern = re.compile(r"metadata\s*\.\s*create_all|\bcreate_all\s*\(")
    offenders: list[str] = []
    for top in ("core", "contracts", "modules", "scripts", "tests"):
        for path in (ROOT / top).rglob("*.py"):
            if path == Path(__file__) or ".venv" in path.parts:
                continue
            if pattern.search(path.read_text()):
                offenders.append(str(path.relative_to(ROOT)))
    assert offenders == []
