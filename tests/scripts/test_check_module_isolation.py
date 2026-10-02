import subprocess
import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).parents[2]))

from scripts.check_module_isolation import is_allowed, main, violations


def git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
        cwd=repo,
        check=True,
        capture_output=True,
    )


def write(repo: Path, rel: str, text: str = "x\n") -> None:
    p = repo / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    git(tmp_path, "init", "-q", "-b", "main")
    write(tmp_path, "core/a.py")
    write(tmp_path, "modules/sbis/a.py")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-q", "-m", "base")
    git(tmp_path, "checkout", "-q", "-b", "work")
    return tmp_path


def commit(repo: Path) -> None:
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "work")


def test_is_allowed():
    assert is_allowed("modules/sbis/x/y.py", "sbis")
    assert is_allowed("contracts/sbis_bungalow.py", "sbis")
    assert is_allowed("docs/anything.md", "sbis")
    assert not is_allowed("modules/sbis2/x.py", "sbis")
    assert not is_allowed("modules/sbis", "sbis")
    assert not is_allowed("modules/civ/x.py", "sbis")
    assert not is_allowed("contracts/civ_pano.py", "sbis")
    assert not is_allowed("contracts/sbis.py", "sbis")
    assert not is_allowed("core/a.py", "sbis")
    assert not is_allowed("Makefile", "sbis")
    assert not is_allowed("docsx/a.md", "sbis")


def test_violations_sorted_unique():
    files = ["core/b.py", "modules/sbis/a.py", "core/a.py", "core/b.py"]
    assert violations(files, "sbis") == ["core/a.py", "core/b.py"]


def test_pass_committed(repo: Path, capsys: pytest.CaptureFixture[str]):
    write(repo, "modules/sbis/new.py")
    write(repo, "contracts/sbis_x.py")
    write(repo, "docs/n.md")
    commit(repo)
    assert main(["main", "--module", "sbis"], cwd=repo) == 0
    assert "passed" in capsys.readouterr().out


def test_no_changes_passes(repo: Path):
    assert main(["main", "--module", "sbis"], cwd=repo) == 0


def test_fail_committed(repo: Path, capsys: pytest.CaptureFixture[str]):
    write(repo, "modules/sbis/new.py")
    write(repo, "core/a.py", "changed\n")
    commit(repo)
    assert main(["main", "--module", "sbis"], cwd=repo) == 1
    out = capsys.readouterr().out
    assert "core/a.py" in out
    assert "modules/sbis/new.py" not in out


def test_fail_uncommitted_and_untracked(repo: Path, capsys: pytest.CaptureFixture[str]):
    write(repo, "core/a.py", "edited\n")
    write(repo, "scripts/new.py")
    assert main(["main", "--module", "sbis"], cwd=repo) == 1
    out = capsys.readouterr().out
    assert "core/a.py" in out
    assert "scripts/new.py" in out


def test_rename_out_of_module_caught(repo: Path, capsys: pytest.CaptureFixture[str]):
    git(repo, "mv", "modules/sbis/a.py", "core/moved.py")
    commit(repo)
    assert main(["main", "--module", "sbis"], cwd=repo) == 1
    assert "core/moved.py" in capsys.readouterr().out


def test_other_module_fails(repo: Path):
    write(repo, "modules/civ/a.py")
    commit(repo)
    assert main(["main", "--module", "sbis"], cwd=repo) == 1
    assert main(["main", "--module", "civ"], cwd=repo) == 0


def test_bad_ref_is_error(repo: Path):
    assert main(["no-such-ref", "--module", "sbis"], cwd=repo) == 2


def test_bad_module_key(repo: Path):
    assert main(["main", "--module", "../core"], cwd=repo) == 2
