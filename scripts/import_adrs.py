"""Import rmi-platform's ADRs and OWNER_RULINGS into docs/decisions/.

    python scripts/import_adrs.py [--source DIR] [--dest docs/decisions] [--date YYYY-MM-DD]

Defaults: source ~/sources/rmi-platform, date today (UTC).

- `<source>/docs/adr/NNNN-slug.md` -> `<dest>/NNNN-slug.md` (the ADR keeps its number).
- `<source>/docs/planning/OWNER_RULINGS.md` -> `<dest>/0100-owner-rulings.md`.
- Front matter is added; the original text follows it byte for byte.
- ADR status comes from the `**Status**:` line: Accepted -> ruled, Proposed -> open,
  Superseded -> superseded. The original line is kept as `source_status`.
- `date` is the first date on the status line (rulings: newest heading date), else the import date.
- Re-running overwrites the same files, so the import is repeatable.
Exit 1 if any file could not be imported (the others are still written).
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

RULINGS_NUMBER = "0100"
STATUS_MAP = {"accepted": "ruled", "proposed": "open", "superseded": "superseded"}
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
ADR_NAME_RE = re.compile(r"^(\d{4})-(.+)\.md$")
STATUS_RE = re.compile(r"^\*\*Status\*\*:\s*(.+)$", re.MULTILINE)


def front_matter(fields: dict[str, str]) -> str:
    lines = [f"{key}: {value}" for key, value in fields.items()]
    return "---\n" + "\n".join(lines) + "\n---\n"


def import_adr(text: str, rel_path: str, today: str) -> str:
    """Return the decision file text for one ADR; raise ValueError if it cannot be imported."""
    if text.startswith("---"):
        raise ValueError("already has front matter")
    match = STATUS_RE.search(text)
    if not match:
        raise ValueError("no **Status**: line")
    status_line = match.group(1).strip()
    word = re.match(r"[A-Za-z]+", status_line)
    status = STATUS_MAP.get(word.group(0).lower()) if word else None
    if status is None:
        raise ValueError(f"unknown status: {status_line!r}")
    found = DATE_RE.search(status_line)
    fields = {
        "status": status,
        "kind": "architecture",
        "date": found.group(0) if found else today,
        "refs": "[]",
        "source_status": json.dumps(status_line, ensure_ascii=False),
        "imported_from": rel_path,
        "imported_on": today,
    }
    return front_matter(fields) + text


def import_rulings(text: str, rel_path: str, today: str) -> str:
    if text.startswith("---"):
        raise ValueError("already has front matter")
    dates = re.findall(r"^## (\d{4}-\d{2}-\d{2})\b", text, re.MULTILINE)
    fields = {
        "status": "ruled",
        "kind": "ruling",
        "date": max(dates) if dates else today,
        "refs": "[]",
        "imported_from": rel_path,
        "imported_on": today,
    }
    return front_matter(fields) + text


def read(path: Path) -> str:
    with open(path, encoding="utf-8", newline="") as f:
        return f.read()


def write(path: Path, text: str) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def run(source: Path, dest: Path, today: str) -> tuple[list[Path], list[str]]:
    """Import everything; return (files written, problems)."""
    written: list[Path] = []
    problems: list[str] = []
    dest.mkdir(parents=True, exist_ok=True)
    prefix = source.name

    adr_dir = source / "docs" / "adr"
    for path in sorted(adr_dir.glob("*.md")) if adr_dir.is_dir() else []:
        name = ADR_NAME_RE.match(path.name)
        if not name:  # README.md and anything else that is not an ADR
            continue
        rel = f"{prefix}/docs/adr/{path.name}"
        try:
            out = import_adr(read(path), rel, today)
        except ValueError as exc:
            problems.append(f"{rel}: {exc}")
            continue
        target = dest / path.name
        write(target, out)
        written.append(target)

    rulings = source / "docs" / "planning" / "OWNER_RULINGS.md"
    rel = f"{prefix}/docs/planning/OWNER_RULINGS.md"
    if rulings.is_file():
        try:
            out = import_rulings(read(rulings), rel, today)
        except ValueError as exc:
            problems.append(f"{rel}: {exc}")
        else:
            target = dest / f"{RULINGS_NUMBER}-owner-rulings.md"
            write(target, out)
            written.append(target)
    else:
        problems.append(f"{rel}: not found")
    return written, problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Import rmi-platform ADRs into docs/decisions")
    parser.add_argument("--source", type=Path, default=Path.home() / "sources" / "rmi-platform")
    parser.add_argument("--dest", type=Path, default=Path("docs/decisions"))
    parser.add_argument("--date", default=dt.datetime.now(dt.UTC).strftime("%Y-%m-%d"))
    args = parser.parse_args(argv)
    if not DATE_RE.fullmatch(args.date):
        print(f"bad --date: {args.date}")
        return 1
    written, problems = run(args.source.expanduser(), args.dest, args.date)
    for path in written:
        print(f"wrote {path}")
    for problem in problems:
        print(f"PROBLEM {problem}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
