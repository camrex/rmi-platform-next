import argparse
import subprocess
import sys
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="Check module isolation.")
    parser.add_argument("base_ref", help="Base git ref to compare against (e.g., main)")
    parser.add_argument("--module", required=True, help="Module key to check isolation for")
    args = parser.parse_args()

    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", args.base_ref],
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"Error running git diff: {e.stderr}", file=sys.stderr)
        sys.exit(1)

    files = result.stdout.splitlines()
    invalid_files = []

    module_prefix = f"modules/{args.module}/"
    contract_prefix = f"contracts/{args.module}_"
    docs_prefix = "docs/"

    for file in files:
        if not (
            file.startswith(module_prefix)
            or file.startswith(contract_prefix)
            or file.startswith(docs_prefix)
        ):
            invalid_files.append(file)

    if invalid_files:
        print(f"Module isolation violation for module '{args.module}':")
        for file in invalid_files:
            print(f"  - {file}")
        sys.exit(1)

    print(f"Module isolation check passed for module '{args.module}'.")

if __name__ == "__main__":
    main()
