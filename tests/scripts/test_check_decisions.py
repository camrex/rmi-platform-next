from pathlib import Path

from scripts.check_decisions import check_front_matter


def test_valid_front_matter():
    content = "---\nstatus: ruled\nkind: architecture\ndate: 2026-10-03\nrefs: []\n---\n"
    # We need to write to a file because check_front_matter reads from a file
    tmp_file = Path("test_decision.md")
    tmp_file.write_text(content)
    try:
        valid, error = check_front_matter(tmp_file)
        assert valid
        assert error is None
    finally:
        tmp_file.unlink()


def test_missing_front_matter():
    content = "# No front matter"
    tmp_file = Path("test_decision_no_fm.md")
    tmp_file.write_text(content)
    try:
        valid, error = check_front_matter(tmp_file)
        assert not valid
        assert error is not None and "Missing or invalid front matter block" in error
    finally:
        tmp_file.unlink()


def test_missing_field():
    content = "---\nstatus: ruled\nkind: architecture\ndate: 2026-10-03\n---\n"  # Missing refs
    tmp_file = Path("test_decision_missing_field.md")
    tmp_file.write_text(content)
    try:
        valid, error = check_front_matter(tmp_file)
        assert not valid
        assert error is not None and "Missing required field: refs" in error
    finally:
        tmp_file.unlink()


def test_invalid_status():
    content = "---\nstatus: unknown\nkind: architecture\ndate: 2026-10-03\nrefs: []\n---\n"
    tmp_file = Path("test_decision_invalid_status.md")
    tmp_file.write_text(content)
    try:
        valid, error = check_front_matter(tmp_file)
        assert not valid
        assert error is not None and "Invalid status: unknown" in error
    finally:
        tmp_file.unlink()


def test_invalid_date():
    content = "---\nstatus: ruled\nkind: architecture\ndate: 10-03-2026\nrefs: []\n---\n"
    tmp_file = Path("test_decision_invalid_date.md")
    tmp_file.write_text(content)
    try:
        valid, error = check_front_matter(tmp_file)
        assert not valid
        assert error is not None and "Invalid date format: 10-03-2026" in error
    finally:
        tmp_file.unlink()
