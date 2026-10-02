#!/usr/bin/env python3
import os
import sys
from pathlib import Path

MAX_LINES = 500
TARGET_DIRS = ['core', 'contracts', 'modules', 'scripts']

def check_files(root='.'):
    failed = False
    for dir_name in TARGET_DIRS:
        path = Path(root) / dir_name
        if not path.is_dir():
            continue
        
        for py_file in path.rglob('*.py'):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    lines = sum(1 for _ in f)
                    if lines > MAX_LINES:
                        print(f"{py_file}: {lines} lines (max {MAX_LINES})")
                        failed = True
            except Exception as e:
                print(f"Error reading {py_file}: {e}")
                failed = True
    
    return failed

if __name__ == "__main__":
    import sys
    root_dir = sys.argv[1] if len(sys.argv) > 1 else '.'
    if check_files(root_dir):
        sys.exit(1)

