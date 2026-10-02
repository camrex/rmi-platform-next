import sys
from pathlib import Path


def main():
    module_keys = {"sbis", "civ", "cvs", "tivs", "pm", "pmfee", "pmfin"}

    # Add directories in modules/ to module_keys
    modules_dir = Path("modules")
    if modules_dir.exists() and modules_dir.is_dir():
        for entry in modules_dir.iterdir():
            if entry.is_dir():
                module_keys.add(entry.name)

    core_dir = Path("core")
    if not core_dir.exists() or not core_dir.is_dir():
        print(f"Error: core directory not found at {core_dir.absolute()}")
        sys.exit(1)

    found_violations = []
    for path in core_dir.rglob("*"):
        name = path.stem if path.is_file() else path.name
        if name in module_keys:
            found_violations.append(str(path))

    if found_violations:
        print("Core-is-clean check failed. The following paths under core/ name a module key:")
        for v in found_violations:
            print(f"  - {v}")
        sys.exit(1)

    print("Core-is-clean check passed.")
    sys.exit(0)


if __name__ == "__main__":
    main()
