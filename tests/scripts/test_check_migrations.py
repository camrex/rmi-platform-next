"""scripts/check_migrations.py: every chain upgrades from scratch and matches its models.

The database tests build throwaway chains in a temp repo root and need the box's PostgreSQL
(they skip without it, or fail with RMI_REQUIRE_DB=1, like the rest of the harness)."""

import asyncio
import os
import shutil
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from scripts import check_migrations
from tests.harness import db

REPO = Path(__file__).resolve().parents[2]
SAMPLE_ENV = REPO / "tests" / "harness" / "sample_chain" / "env.py"

REVISION = """
import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None


def upgrade() -> None:
    op.create_table(
        "{table}",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("label", sa.Text, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("{table}")
"""

METADATA = """
import sqlalchemy as sa

target_metadata = sa.MetaData()
sa.Table(
    "{table}", target_metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("label", {label_type}, nullable=False),
    {extra}
)
"""


def make_chain(
    root: Path,
    key: str,
    *,
    metadata: str | None = "ok",
    revision: str | None = None,
    label_type: str = "sa.Text",
    extra: str = "",
) -> db.Chain:
    """A one-table module chain under root/modules/<key>/migrations."""
    table = f"{key}_thing"
    location = root / "modules" / key / "migrations"
    (location / "versions").mkdir(parents=True)
    env = SAMPLE_ENV.read_text().replace("alembic_version_harness_sample", f"alembic_version_{key}")
    (location / "env.py").write_text(env)
    (location / "versions" / "0001.py").write_text(
        revision if revision is not None else REVISION.format(table=table)
    )
    if metadata is not None:
        (location / "metadata.py").write_text(
            METADATA.format(table=table, label_type=label_type, extra=extra)
        )
    return db.Chain(key, location)


@pytest.fixture
def admin() -> URL:
    url = db.admin_url()
    problem = asyncio.run(db.server_error(url))
    if problem is not None:
        message = f"PostgreSQL not available ({problem}); see docs/TESTING.md"
        if os.environ.get(db.REQUIRE_DB_ENV) == "1":
            pytest.fail(message, pytrace=False)
        pytest.skip(message)
    return url


async def test_matching_chains_pass(tmp_path: Path, admin: URL) -> None:
    chains = [make_chain(tmp_path, "alpha"), make_chain(tmp_path, "beta")]
    assert await check_migrations.check_chains(chains, admin) == []


async def test_model_column_missing_from_migrations_is_drift(tmp_path: Path, admin: URL) -> None:
    chain = make_chain(tmp_path, "alpha", extra='sa.Column("added", sa.Integer),')
    problems = await check_migrations.check_chains([chain], admin)
    assert len(problems) == 1
    assert problems[0].startswith("alpha: drift:")
    assert "added" in problems[0]


async def test_column_type_change_is_drift(tmp_path: Path, admin: URL) -> None:
    chain = make_chain(tmp_path, "alpha", label_type="sa.Integer")
    problems = await check_migrations.check_chains([chain], admin)
    assert problems and all(p.startswith("alpha: drift:") for p in problems)


async def test_table_in_migrations_but_not_in_models_is_drift(tmp_path: Path, admin: URL) -> None:
    chain = make_chain(tmp_path, "alpha")
    (chain.location / "metadata.py").write_text(
        "import sqlalchemy as sa\n\ntarget_metadata = sa.MetaData()\n"
    )
    problems = await check_migrations.check_chains([chain], admin)
    assert len(problems) == 1
    assert "alpha_thing" in problems[0]


async def test_chain_without_metadata_fails(tmp_path: Path, admin: URL) -> None:
    chain = make_chain(tmp_path, "alpha", metadata=None)
    problems = await check_migrations.check_chains([chain], admin)
    assert len(problems) == 1
    assert "no metadata.py" in problems[0]


async def test_failing_upgrade_is_reported_and_others_still_checked(
    tmp_path: Path, admin: URL
) -> None:
    broken = make_chain(tmp_path, "alpha", revision="raise RuntimeError('boom')\n")
    fine = make_chain(tmp_path, "beta", extra='sa.Column("added", sa.Integer),')
    problems = await check_migrations.check_chains([broken, fine], admin)
    assert any(p.startswith("alpha: upgrade head failed") for p in problems)
    assert any(p.startswith("beta: drift:") for p in problems)


async def test_scratch_database_is_dropped(tmp_path: Path, admin: URL) -> None:
    async def databases() -> set[str]:
        engine = create_async_engine(admin, poolclass=NullPool)
        try:
            async with engine.connect() as conn:
                rows = await conn.execute(text("select datname from pg_database"))
                return {row[0] for row in rows}
        finally:
            await engine.dispose()

    before = await databases()
    await check_migrations.check_chains([make_chain(tmp_path, "alpha")], admin)
    assert await databases() == before


def test_no_chains_passes_without_a_server(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv(db.ADMIN_DSN_ENV, "postgresql://nobody@/nothing?host=/nonexistent")
    assert check_migrations.run(tmp_path) == 0
    assert "no migration chains" in capsys.readouterr().out


def test_unreachable_server_skips_unless_required(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    make_chain(tmp_path, "alpha")
    monkeypatch.setenv(db.ADMIN_DSN_ENV, "postgresql://nobody@/nothing?host=/nonexistent")
    monkeypatch.delenv(db.REQUIRE_DB_ENV, raising=False)
    assert check_migrations.run(tmp_path) == 0
    assert "SKIPPED" in capsys.readouterr().out
    monkeypatch.setenv(db.REQUIRE_DB_ENV, "1")
    assert check_migrations.run(tmp_path) == 1
    assert "FAILED" in capsys.readouterr().out


def test_the_repo_itself_passes() -> None:
    """Core and every module chain in this repo (none yet is fine; a drifting one is not)."""
    if shutil.which("psql") is None and not (Path("/var/run/postgresql").exists()):
        pytest.skip("no PostgreSQL on this machine")
    assert check_migrations.run(REPO) == 0
