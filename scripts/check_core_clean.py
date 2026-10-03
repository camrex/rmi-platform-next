"""Fail if anything under core/ names a module key (PROPOSAL §3.1, "CI greps `core/`").

Two checks:
- no file or directory under `core/` is named after a module key;
- no line of a source file under `core/src/` contains a module key as a whole word
  (`sbis`, `/sbis/`, `"sbis.x"` match; `sbis_like`, `SBIS` do not). `core/tests/` may use
  module names as fixtures and is not scanned for content.

Keys: the old platform's modules plus every directory in `modules/`.
"""

import re
import sys
from pathlib import Path

KNOWN_KEYS = {"sbis", "civ", "cvs", "tivs", "pm", "pmfee", "pmfin"}
# `catalog` and `pricing` will be module keys (B6, B8), but the core's `Ref` forms
# (`catalog.item:`, `pricing.price:`, PROPOSAL §4.1) and the manifest's `catalog_refs` (§3.2, §7.5)
# name them by design. They are exempt from the content check only, never from file names.
CONTENT_EXEMPT = {"catalog", "pricing"}
CONTENT_SUFFIXES = {".py", ".toml", ".md", ".html", ".js", ".css", ".txt", ".ini", ".cfg"}


def module_keys(root: Path) -> set[str]:
    keys = set(KNOWN_KEYS)
    modules_dir = root / "modules"
    if modules_dir.is_dir():
        keys |= {e.name for e in modules_dir.iterdir() if e.is_dir() and not e.name.startswith(".")}
    return keys


def violations(root: Path) -> list[str]:
    keys = module_keys(root)
    alternatives = "|".join(sorted(map(re.escape, keys - CONTENT_EXEMPT)))
    word = re.compile(rf"(?<![A-Za-z0-9_])({alternatives})(?![A-Za-z0-9_])")
    found: list[str] = []
    for path in sorted((root / "core").rglob("*")):
        if "__pycache__" in path.parts:
            continue
        name = path.stem if path.is_file() else path.name
        if name in keys:
            found.append(f"{path.relative_to(root)}: named after a module key")
    src = root / "core" / "src"
    for path in sorted(src.rglob("*")) if src.is_dir() else []:
        if not path.is_file() or path.suffix not in CONTENT_SUFFIXES or "__pycache__" in path.parts:
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            match = word.search(line)
            if match:
                where = f"{path.relative_to(root)}:{number}"
                found.append(f"{where}: names module key {match.group(1)!r}")
    return found


def main() -> None:
    root = Path.cwd()
    if not (root / "core").is_dir():
        print(f"Error: core directory not found at {(root / 'core').absolute()}")
        sys.exit(1)
    found = violations(root)
    if found:
        print("Core-is-clean check failed. The following paths under core/ name a module key:")
        for v in found:
            print(f"  - {v}")
        sys.exit(1)
    print("Core-is-clean check passed.")
    sys.exit(0)


if __name__ == "__main__":
    main()
