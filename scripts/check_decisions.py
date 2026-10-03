import re
import sys
from pathlib import Path


def check_front_matter(file_path: Path) -> tuple[bool, str | None]:
    with open(file_path, encoding="utf-8") as f:
        content = f.read()

    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    if not match:
        return False, "Missing or invalid front matter block"

    front_matter = match.group(1)
    lines = front_matter.split("\n")
    fields: dict[str, str] = {}
    for line in lines:
        if ":" in line:
            key, value = line.split(":", 1)
            fields[key.strip()] = value.strip()

    required_fields = ["status", "kind", "date", "refs"]
    for field in required_fields:
        if field not in fields:
            return False, f"Missing required field: {field}"

    valid_statuses = ["ruled", "tabled", "open", "superseded"]
    if fields["status"] not in valid_statuses:
        return False, f"Invalid status: {fields['status']}. Must be one of {valid_statuses}"

    # Basic date check (YYYY-MM-DD)
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", fields["date"]):
        return False, f"Invalid date format: {fields['date']}. Use YYYY-MM-DD"

    return True, None


def main():
    decisions_dir = Path("docs/decisions")
    if not decisions_dir.exists():
        print(f"Decisions directory {decisions_dir} not found")
        sys.exit(1)

    errors = 0
    for file_path in decisions_dir.glob("*.md"):
        if file_path.name == "README.md" or file_path.name == "0000-template.md":
            continue

        valid, error = check_front_matter(file_path)
        if not valid:
            print(f"Error in {file_path}: {error}")
            errors += 1

    if errors > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
