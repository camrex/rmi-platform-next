import sys
import tempfile
from pathlib import Path

from scripts.new_module import create_module


def test_new_module_generation():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        modules_dir = tmp_path / "modules"
        modules_dir.mkdir()

        # We need to ensure the template is available where the script expects it.
        # The script currently uses Path("modules/_template").
        # Since we are running from the project root, it should find it,
        # but create_module uses a hardcoded template path.

        key = "test_mod"
        create_module(key, base_dir=modules_dir)

        manifest_path = modules_dir / key / "manifest.py"
        assert manifest_path.exists()

        # Add modules_dir to sys.path to import the generated module
        sys.path.append(str(modules_dir))
        try:
            # Import the manifest from the newly created module
            # Using __import__ or importlib because the module name is dynamic
            import importlib

            mod = importlib.import_module(f"{key}.manifest")
            assert mod.MANIFEST["key"] == key
            assert mod.MANIFEST["name"] == "Test Mod"
        finally:
            sys.path.remove(str(modules_dir))
