#!/usr/bin/env python3
import argparse
import subprocess
import sys
import re

def main():
    parser = argparse.ArgumentParser(description="Check if changes are isolated to a specific module.")
    parser.add_argument("--base", required=True, help="Base git ref to diff against")
    parser.add_argument("--module", required=True, help="The module key to check isolation for")
    args = parser.parse_args()

    try:
        # Get list of changed files
        # git diff --name-only base_ref
        result = subprocess.run(
            ["git", "diff", "--name-only", args.base],
            capture_output=True,
            text=True,
            check=True
        )
        files = result.stdout.splitlines()
    except subprocess.CalledProcessError as e:
        print(f"Error running git diff: {e}", file=sys.stderr)
        sys.exit(1)

    allowed_patterns = [
        rf"^modules/{re.escape(args.module)}/",
        rf"^contracts/{re.escape(args.module)}_[^/]*",
        rf"^docs/"
    ]
    
    # We use regex to check if the file matches any of the allowed patterns
    # If it doesn't match any, it's a violation.
    violations = []
    for file in files:
        is_allowed = False
        for pattern in allowed_patterns:
            if re.match(pattern, file):
                is_allowed = True
                break
        if not is_allowed:
            violations.append(file)

    if violations:
        print(f"Module isolation violation for module '{args.module}'! The following files were touched outside the allowed paths:", file=sys.stderr)
        for v in violations:
            print(f"  - {v}", file=sys.stderr)
        sys.exit(1)

    print(f"Module isolation check passed for module '{args.module}'.")
    sys.exit(0)

if __name__ == "__main__":
    main()
