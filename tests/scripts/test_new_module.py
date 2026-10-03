import importlib
import sys
import tempfile
from pathlib import Path

from rmi_core.manifest import ModuleManifest
from rmi_core.testing.contract import assert_contract
from scripts.new_module import create_module


def test_new_module_generation() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        modules_dir = Path(tmp_dir) / "modules"
        modules_dir.mkdir()

        key = "test_mod"
        create_module(key, base_dir=modules_dir)

        assert (modules_dir / key / "manifest.py").exists()
        assert (modules_dir / key / "tests" / "test_contract.py").exists()
        pyproject = (modules_dir / key / "pyproject.toml").read_text()
        assert "{{" not in pyproject
        assert 'test_mod = "modules.test_mod.manifest:manifest"' in pyproject

        sys.path.append(str(modules_dir))
        try:
            mod = importlib.import_module(f"{key}.manifest")
            manifest = mod.manifest
            assert isinstance(manifest, ModuleManifest)
            assert manifest.key == key
            assert manifest.display_name == "Test Mod"
            assert_contract(manifest, candidates=[])
        finally:
            sys.path.remove(str(modules_dir))
            for name in [n for n in sys.modules if n == key or n.startswith(f"{key}.")]:
                del sys.modules[name]
