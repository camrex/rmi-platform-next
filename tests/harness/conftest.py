from pathlib import Path

import pytest

from tests.harness import db


@pytest.fixture(scope="session")
def migration_chains() -> list[db.Chain]:
    """The harness tests build the schema from their own one-table chain."""
    return [db.Chain("harness_sample", Path(__file__).parent / "sample_chain")]
