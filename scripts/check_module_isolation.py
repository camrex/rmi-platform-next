"""Module-isolation check (PROPOSAL §3.3, PLAN B1.4).

Work on module `<key>` may touch only `modules/<key>/`, `contracts/<key>_*` and `docs/`.
Usage: python scripts/check_module_isolation.py <base-ref> --module <key>

The diff is `<base-ref>...HEAD` (changes on this branch since it left the base), plus
uncommitted changes to tracked files and untracked files, so it also works before a commit.
Renames are listed as a delete and an add, so moving a file out of a module is caught.
"""

import argparse
import re
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

KEY_RE = re.compile(r"[a-z][a-z0-9_]*")
ALWAYS_ALLOWED = ("docs/", "uv.lock")


def is_allowed(path: str, module: str) -> bool:
    """True if `path` (repo-relative, `/` separated) is inside the module's own territory."""
    return (
        path.startswith(f"modules/{module}/")
        or path.startswith(f"contracts/{module}_")
        or path.startswith(ALWAYS_ALLOWED)
    )


def violations(files: Sequence[str], module: str) -> list[str]:
    return sorted({f for f in files if not is_allowed(f, module)})


def _git(args: list[str], cwd: Path) -> list[str]:
    out = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True).stdout
    return [line for line in out.splitlines() if line]


def changed_files(base_ref: str, cwd: Path) -> list[str]:
    """Paths changed since `base_ref`: committed, staged or unstaged, and untracked."""
    committed = _git(["diff", "--name-only", "--no-renames", f"{base_ref}...HEAD"], cwd)
    working = _git(["diff", "--name-only", "--no-renames", "HEAD"], cwd)
    untracked = _git(["ls-files", "--others", "--exclude-standard"], cwd)
    return sorted(set(committed) | set(working) | set(untracked))


def main(argv: Sequence[str] | None = None, cwd: Path | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fail if a diff leaves one module's territory.")
    parser.add_argument("base_ref", help="git ref the work branched from, e.g. origin/main")
    parser.add_argument("--module", required=True, help="module key, e.g. sbis")
    args = parser.parse_args(argv)

    if not KEY_RE.fullmatch(args.module):
        print(f"Invalid module key {args.module!r}: use lowercase letters, digits, underscore.")
        return 2
    try:
        files = changed_files(args.base_ref, cwd or Path.cwd())
    except subprocess.CalledProcessError as e:
        print(f"git failed: {(e.stderr or '').strip()}", file=sys.stderr)
        return 2

    bad = violations(files, args.module)
    if bad:
        print(
            f"Module isolation failed for '{args.module}': changes outside "
            f"modules/{args.module}/, contracts/{args.module}_* and docs/:"
        )
        for f in bad:
            print(f"  - {f}")
        return 1
    print(f"Module isolation passed for '{args.module}' ({len(files)} changed files).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
