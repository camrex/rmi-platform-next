import sys
from pathlib import Path

# Add root to sys.path to allow importing from scripts/
sys.path.append(str(Path(__file__).parents[2]))


import pytest

from scripts.check_file_size import check_files


@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    core = tmp_path / "core"
    core.mkdir()
    contracts = tmp_path / "contracts"
    contracts.mkdir()
    modules = tmp_path / "modules"
    modules.mkdir()
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    return tmp_path


def test_check_file_size_passes_with_short_files(tmp_project: Path) -> None:
    (tmp_project / "core" / "short.py").write_text("print('hello')" * 10)
    assert check_files(str(tmp_project)) is False


def test_check_file_size_fails_with_long_file(tmp_project: Path) -> None:
    (tmp_project / "core" / "long.py").write_text("\n" * 501)
    assert check_files(str(tmp_project)) is True


def test_check_file_size_ignores_non_py_files(tmp_project: Path) -> None:
    (tmp_project / "core" / "long.txt").write_text("\n" * 501)
    assert check_files(str(tmp_project)) is False


def test_check_file_size_checks_all_dirs(tmp_project: Path) -> None:
    (tmp_project / "contracts" / "long.py").write_text("\n" * 501)
    assert check_files(str(tmp_project)) is True

    # Clean up and check modules
    (tmp_project / "contracts" / "long.py").unlink()
    (tmp_project / "modules" / "long.py").write_text("\n" * 501)
    assert check_files(str(tmp_project)) is True

    # Clean up and check scripts
    (tmp_project / "modules" / "long.py").unlink()
    (tmp_project / "scripts" / "long.py").write_text("\n" * 501)
    assert check_files(str(tmp_project)) is True
