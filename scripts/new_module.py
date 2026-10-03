import argparse
import shutil
from pathlib import Path


def generate_name(key: str) -> str:
    return key.replace("_", " ").title()


def create_module(key: str, base_dir: Path = Path("modules")):
    template_dir = Path("modules/_template")
    target_dir = base_dir / key

    if target_dir.exists():
        print(f"Error: Module {key} already exists.")
        exit(1)

    shutil.copytree(template_dir, target_dir)

    name = generate_name(key)

    for path in target_dir.rglob("*"):
        if path.is_file() and (path.suffix == ".py" or path.suffix == ".md"):
            content = path.read_text()
            content = content.replace("{{MODULE_KEY}}", key)
            content = content.replace("{{MODULE_NAME}}", name)
            path.write_text(content)

    print(f"Module {key} created successfully at {target_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create a new module from template")
    parser.add_argument("key", help="The key of the new module (e.g. my_module)")
    parser.add_argument(
        "--base", type=Path, default=Path("modules"), help="Base directory for modules"
    )
    args = parser.parse_args()
    create_module(args.key, args.base)
