from pathlib import Path

import pytest

from scripts.check_decisions import check_front_matter
from scripts.import_adrs import import_adr, main, run

TODAY = "2026-10-03"
ADR = (
    "# 0001 — Tooling\n\n**Status**: Accepted (2026-06-03) · **Relates to**: ADR 0002\n\n"
    "## Context\n\nText: with colons.\r\n"
)
RULINGS = "# Owner rulings\n\n## 2026-09-29 — b\n\nx\n\n## 2026-08-20 — a\n\ny\n"


def make_source(tmp_path: Path) -> Path:
    src = tmp_path / "rmi-platform"
    adr = src / "docs" / "adr"
    adr.mkdir(parents=True)
    (adr / "README.md").write_text("# index\n")
    (adr / "0001-tooling.md").write_bytes(ADR.encode())
    (adr / "0002-draft.md").write_text("# 0002\n\n**Status**: Proposed (2026-07-25)\n")
    old = "# 0003\n\n**Status**: Superseded by 0016 (2026-08-14) · originally Accepted\n"
    (adr / "0003-old.md").write_text(old)
    planning = src / "docs" / "planning"
    planning.mkdir(parents=True)
    (planning / "OWNER_RULINGS.md").write_text(RULINGS)
    return src


def test_status_mapping_and_body_unchanged(tmp_path: Path) -> None:
    src = make_source(tmp_path)
    dest = tmp_path / "out"
    written, problems = run(src, dest, TODAY)
    assert problems == []
    assert sorted(p.name for p in written) == [
        "0001-tooling.md",
        "0002-draft.md",
        "0003-old.md",
        "0100-owner-rulings.md",
    ]
    out = (dest / "0001-tooling.md").read_bytes().decode()
    assert "status: ruled\n" in out
    assert "date: 2026-06-03\n" in out
    assert "imported_from: rmi-platform/docs/adr/0001-tooling.md\n" in out
    assert f"imported_on: {TODAY}\n" in out
    assert out.endswith("\n---\n" + ADR)  # body byte for byte, CRLF included
    assert "status: open\n" in (dest / "0002-draft.md").read_text()
    assert "status: superseded\n" in (dest / "0003-old.md").read_text()


def test_rulings_file(tmp_path: Path) -> None:
    src = make_source(tmp_path)
    run(src, tmp_path / "out", TODAY)
    out = (tmp_path / "out" / "0100-owner-rulings.md").read_text()
    assert "status: ruled\n" in out
    assert "date: 2026-09-29\n" in out
    assert out.endswith(RULINGS)


def test_output_passes_checker(tmp_path: Path) -> None:
    src = make_source(tmp_path)
    written, _ = run(src, tmp_path / "out", TODAY)
    for path in written:
        assert check_front_matter(path) == (True, None), path


def test_rerun_is_repeatable(tmp_path: Path) -> None:
    src = make_source(tmp_path)
    run(src, tmp_path / "out", TODAY)
    first = {p.name: p.read_bytes() for p in (tmp_path / "out").iterdir()}
    run(src, tmp_path / "out", TODAY)
    assert first == {p.name: p.read_bytes() for p in (tmp_path / "out").iterdir()}


def test_bad_adrs_reported_others_still_written(tmp_path: Path) -> None:
    src = make_source(tmp_path)
    (src / "docs" / "adr" / "0004-nostatus.md").write_text("# 0004\n\nno status\n")
    (src / "docs" / "adr" / "0005-odd.md").write_text("# 0005\n\n**Status**: Maybe (2026-01-01)\n")
    written, problems = run(src, tmp_path / "out", TODAY)
    assert len(problems) == 2
    assert not (tmp_path / "out" / "0004-nostatus.md").exists()
    assert len(written) == 4


def test_existing_front_matter_refused() -> None:
    with pytest.raises(ValueError):
        import_adr("---\nstatus: ruled\n---\n" + ADR, "x", TODAY)


def test_missing_rulings_is_a_problem(tmp_path: Path) -> None:
    src = make_source(tmp_path)
    (src / "docs" / "planning" / "OWNER_RULINGS.md").unlink()
    _, problems = run(src, tmp_path / "out", TODAY)
    assert len(problems) == 1


def test_main_exit_codes(tmp_path: Path) -> None:
    src = make_source(tmp_path)
    args = ["--source", str(src), "--dest", str(tmp_path / "out"), "--date", TODAY]
    assert main(args) == 0
    assert main(args[:-1] + ["nope"]) == 1
