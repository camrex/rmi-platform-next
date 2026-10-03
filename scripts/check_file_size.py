#!/usr/bin/env python3
"""Fail if any .py file under the checked folders is over MAX_LINES lines (PROPOSAL §5)."""

import sys
from pathlib import Path

MAX_LINES = 500
TARGET_DIRS = ["core", "contracts", "modules", "scripts", "tests"]


def check_files(root: str = ".") -> bool:
    """Return True if any file is over the limit (the check failed)."""
    failed = False
    for dir_name in TARGET_DIRS:
        path = Path(root) / dir_name
        if not path.is_dir():
            continue

        for py_file in path.rglob("*.py"):
            try:
                with open(py_file, encoding="utf-8") as f:
                    lines = sum(1 for _ in f)
                if lines > MAX_LINES:
                    print(f"{py_file}: {lines} lines (max {MAX_LINES})")
                    failed = True
            except OSError as e:
                print(f"Error reading {py_file}: {e}")
                failed = True

    return failed


if __name__ == "__main__":
    root_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    if check_files(root_dir):
        sys.exit(1)
