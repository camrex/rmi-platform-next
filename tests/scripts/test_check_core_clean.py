import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


class TestCoreClean(unittest.TestCase):
    def run_check_script(self, temp_dir: str) -> subprocess.CompletedProcess[str]:
        # Run the script using the current python interpreter
        # We need to pass the temp_dir as the working directory
        result = subprocess.run(
            ["python3", "scripts/check_core_clean.py"], cwd=temp_dir, capture_output=True, text=True
        )
        return result

    def test_core_clean_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            (tmp_path / "scripts").mkdir()
            # Copy the script to the temp dir
            shutil.copy("scripts/check_core_clean.py", tmp_path / "scripts/check_core_clean.py")

            (tmp_path / "core").mkdir()
            (tmp_path / "modules").mkdir()

            # Add some clean files
            (tmp_path / "core/main.py").touch()
            (tmp_path / "core/utils.py").touch()

            res = self.run_check_script(tmpdir)
            self.assertEqual(res.returncode, 0)
            self.assertIn("Core-is-clean check passed", res.stdout)

    def test_core_clean_fails_with_explicit_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            (tmp_path / "scripts").mkdir()
            shutil.copy("scripts/check_core_clean.py", tmp_path / "scripts/check_core_clean.py")

            (tmp_path / "core").mkdir()
            (tmp_path / "modules").mkdir()

            # Add a file with a module key name
            (tmp_path / "core/sbis.py").touch()

            res = self.run_check_script(tmpdir)
            self.assertEqual(res.returncode, 1)
            self.assertIn("Core-is-clean check failed", res.stdout)
            self.assertIn("core/sbis.py", res.stdout)

    def test_core_clean_fails_with_module_dir_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            (tmp_path / "scripts").mkdir()
            shutil.copy("scripts/check_core_clean.py", tmp_path / "scripts/check_core_clean.py")

            (tmp_path / "core").mkdir()
            (tmp_path / "modules").mkdir()

            # Add a module directory
            (tmp_path / "modules/my_module").mkdir()
            # Add a file in core with that name
            (tmp_path / "core/my_module.py").touch()

            res = self.run_check_script(tmpdir)
            self.assertEqual(res.returncode, 1)
            self.assertIn("Core-is-clean check failed", res.stdout)
            self.assertIn("core/my_module.py", res.stdout)


if __name__ == "__main__":
    unittest.main()
